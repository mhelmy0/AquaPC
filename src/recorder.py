"""
Recorder for RTP Video Streaming Client
Handles recording video frames to file with async writing
"""

import cv2
import os
import logging
import time
import threading
import queue
from datetime import datetime
from typing import Optional
import numpy as np


class Recorder:
    """Records video frames to file using OpenCV VideoWriter with async writing"""

    def __init__(self, output_dir: str, filename_pattern: str,
                 format: str = "mp4", codec: str = "h264", fps: int = 30,
                 async_write: bool = True, write_queue_size: int = 100,
                 logger=None):
        """
        Initialize recorder

        Args:
            output_dir: Output directory for recordings
            filename_pattern: Filename pattern with datetime format
            format: Output format (mp4, avi, mkv)
            codec: Video codec (h264, xvid, etc.)
            fps: Frames per second for recording
            async_write: Use async writing (prevents blocking)
            write_queue_size: Size of frame write queue
            logger: Application logger instance
        """
        self.output_dir = output_dir
        self.filename_pattern = filename_pattern
        self.format = format
        self.codec = codec
        self.fps = fps
        self.async_write = async_write
        self.write_queue_size = write_queue_size
        self.logger = logger

        # Recording state
        self.is_recording = False
        self.video_writer: Optional[cv2.VideoWriter] = None
        self.current_filename: Optional[str] = None
        self.frame_count = 0
        self.frames_written = 0
        self.frames_dropped_recording = 0
        self.start_time: Optional[float] = None

        # Async writing
        self.write_queue: Optional[queue.Queue] = None
        self.write_thread: Optional[threading.Thread] = None

        # Codec mapping
        self.codec_map = {
            'h264': 'H264',
            'x264': 'X264',
            'xvid': 'XVID',
            'mjpeg': 'MJPG',
            'mp4v': 'mp4v'
        }

    def start_recording(self, width: int, height: int) -> bool:
        """
        Start recording

        Args:
            width: Frame width
            height: Frame height

        Returns:
            True if recording started successfully, False otherwise
        """
        if self.is_recording:
            self._log_warning("Already recording")
            return False

        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime(self.filename_pattern)
            self.current_filename = os.path.join(
                self.output_dir,
                f"{timestamp}.{self.format}"
            )

            # Get codec fourcc
            codec_name = self.codec_map.get(self.codec.lower(), 'H264')
            fourcc = cv2.VideoWriter_fourcc(*codec_name)

            # Create video writer
            self.video_writer = cv2.VideoWriter(
                self.current_filename,
                fourcc,
                self.fps,
                (width, height)
            )

            if not self.video_writer.isOpened():
                raise RuntimeError("Failed to open video writer")

            self.is_recording = True
            self.frame_count = 0
            self.frames_written = 0
            self.frames_dropped_recording = 0
            self.start_time = time.time()

            # Start async writing thread if enabled
            if self.async_write:
                self.write_queue = queue.Queue(maxsize=self.write_queue_size)
                self.write_thread = threading.Thread(
                    target=self._write_loop,
                    daemon=True
                )
                self.write_thread.start()
                self._log_info(f"Started recording to: {self.current_filename} (async mode)")
            else:
                self._log_info(f"Started recording to: {self.current_filename} (sync mode)")

            if self.logger:
                self.logger.log_recording_event("STARTED", self.current_filename)

            return True

        except Exception as e:
            self._log_error(f"Error starting recording: {e}", exc_info=True)
            if self.logger:
                self.logger.log_error_event("RECORDING_START_FAILED", str(e), "Recorder")
            self.is_recording = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            return False

    def stop_recording(self) -> Optional[str]:
        """
        Stop recording

        Returns:
            Filename of recorded video or None if not recording
        """
        if not self.is_recording:
            self._log_warning("Not currently recording")
            return None

        try:
            self.is_recording = False

            # Wait for async write queue to empty
            if self.async_write and self.write_queue:
                self._log_info("Waiting for write queue to empty...")
                timeout = 10  # 10 second timeout
                start_wait = time.time()

                while not self.write_queue.empty():
                    time.sleep(0.1)
                    if time.time() - start_wait > timeout:
                        self._log_warning("Write queue timeout, some frames may be lost")
                        break

                # Wait for write thread
                if self.write_thread and self.write_thread.is_alive():
                    self.write_thread.join(timeout=2)

            # Release video writer
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None

            # Calculate statistics
            duration = time.time() - self.start_time if self.start_time else 0
            file_size = os.path.getsize(self.current_filename) if self.current_filename else 0

            self._log_info(
                f"Recording stopped: {self.current_filename} "
                f"({self.frames_written} frames written, {self.frames_dropped_recording} dropped, "
                f"{duration:.2f}s, {file_size / 1024 / 1024:.2f} MB)"
            )

            if self.logger:
                self.logger.log_recording_event(
                    "STOPPED",
                    f"{self.current_filename} - {self.frames_written} frames, {duration:.2f}s"
                )

            filename = self.current_filename
            self.current_filename = None
            self.frame_count = 0
            self.frames_written = 0
            self.frames_dropped_recording = 0
            self.start_time = None
            self.write_queue = None

            return filename

        except Exception as e:
            self._log_error(f"Error stopping recording: {e}", exc_info=True)
            return None

    def _write_loop(self) -> None:
        """Background thread for async frame writing"""
        self._log_info("Write thread started")

        while self.is_recording or not self.write_queue.empty():
            try:
                # Get frame from queue with timeout
                frame = self.write_queue.get(timeout=0.5)

                if frame is not None and self.video_writer:
                    self.video_writer.write(frame)
                    self.frames_written += 1

            except queue.Empty:
                continue
            except Exception as e:
                if self.is_recording:
                    self._log_error(f"Error in write loop: {e}", exc_info=True)
                break

        self._log_info(f"Write thread stopped (wrote {self.frames_written} frames)")

    def write_frame(self, frame: np.ndarray) -> bool:
        """
        Write frame to video (async or sync based on configuration)

        Args:
            frame: Frame as numpy array (BGR format)

        Returns:
            True if frame queued/written successfully, False otherwise
        """
        if not self.is_recording:
            return False

        try:
            self.frame_count += 1

            if self.async_write and self.write_queue:
                # Async mode - add to queue
                try:
                    # Make a copy to avoid race conditions
                    frame_copy = frame.copy()
                    self.write_queue.put_nowait(frame_copy)
                    return True
                except queue.Full:
                    self.frames_dropped_recording += 1
                    self._log_warning(f"Recording queue full, dropping frame (total dropped: {self.frames_dropped_recording})")
                    if self.logger and self.frames_dropped_recording % 10 == 0:
                        self.logger.warning(
                            f"Recording dropped {self.frames_dropped_recording} frames",
                            "Recorder"
                        )
                    return False
            else:
                # Sync mode - write directly
                if self.video_writer:
                    self.video_writer.write(frame)
                    self.frames_written += 1
                    return True
                return False

        except Exception as e:
            self._log_error(f"Error writing frame: {e}", exc_info=True)
            if self.logger:
                self.logger.log_error_event("RECORDING_WRITE_ERROR", str(e), "Recorder")
            return False

    def get_status(self) -> dict:
        """
        Get recording status

        Returns:
            Dictionary with recording status
        """
        duration = time.time() - self.start_time if self.start_time and self.is_recording else 0
        queue_size = self.write_queue.qsize() if self.write_queue else 0

        return {
            'is_recording': self.is_recording,
            'filename': self.current_filename,
            'frame_count': self.frame_count,
            'frames_written': self.frames_written,
            'frames_dropped': self.frames_dropped_recording,
            'queue_size': queue_size,
            'duration': duration,
            'fps': self.fps,
            'async_mode': self.async_write
        }

    def _log_info(self, message: str):
        """Log info message"""
        if self.logger:
            self.logger.info(message, "Recorder")
        else:
            logging.info(f"[Recorder] {message}")

    def _log_warning(self, message: str):
        """Log warning message"""
        if self.logger:
            self.logger.warning(message, "Recorder")
        else:
            logging.warning(f"[Recorder] {message}")

    def _log_error(self, message: str, exc_info: bool = False):
        """Log error message"""
        if self.logger:
            self.logger.error(message, "Recorder", exc_info=exc_info)
        else:
            logging.error(f"[Recorder] {message}", exc_info=exc_info)

    def __del__(self):
        """Cleanup on deletion"""
        if self.is_recording:
            self.stop_recording()
