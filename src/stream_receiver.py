"""
Stream Receiver for RTP Video Streaming Client
Handles receiving and decoding RTP H.264 video stream using FFmpeg
"""

import subprocess
import threading
import queue
import logging
import time
import select
import sys
import numpy as np
from typing import Optional, Callable


class StreamReceiver:
    """Receives and decodes RTP video stream using FFmpeg subprocess"""

    def __init__(self, ffmpeg_cmd: list, width: int, height: int,
                 buffer_size: int = 10, frame_drop_threshold: int = 10,
                 stream_timeout: float = 5.0, logger=None):
        """
        Initialize stream receiver

        Args:
            ffmpeg_cmd: FFmpeg command as list of arguments
            width: Video frame width
            height: Video frame height
            buffer_size: Maximum frame buffer size
            frame_drop_threshold: Drop frames if queue exceeds this size
            stream_timeout: Timeout in seconds before declaring stream dead
            logger: Application logger instance
        """
        self.ffmpeg_cmd = ffmpeg_cmd
        self.width = width
        self.height = height
        self.buffer_size = buffer_size
        self.frame_drop_threshold = frame_drop_threshold
        self.stream_timeout = stream_timeout
        self.logger = logger

        # Frame buffer queue
        self.frame_queue = queue.Queue(maxsize=buffer_size)

        # Threading
        self.receive_thread: Optional[threading.Thread] = None
        self.stderr_thread: Optional[threading.Thread] = None
        self.running = False

        # FFmpeg process
        self.ffmpeg_process: Optional[subprocess.Popen] = None

        # Statistics
        self.frames_received = 0
        self.frames_dropped = 0
        self.incomplete_frames = 0
        self.last_frame_time = time.time()
        self.connection_errors = 0

        # Callbacks
        self.on_connect: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None
        self.on_error: Optional[Callable[[str], None]] = None

    def start(self) -> bool:
        """
        Start receiving stream

        Returns:
            True if started successfully, False otherwise
        """
        if self.running:
            self._log_warning("Stream receiver already running")
            return False

        try:
            # Start FFmpeg process
            self.ffmpeg_process = subprocess.Popen(
                self.ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8
            )

            self.running = True
            self.last_frame_time = time.time()

            # Start stderr monitoring thread
            self.stderr_thread = threading.Thread(
                target=self._monitor_ffmpeg_errors,
                daemon=True
            )
            self.stderr_thread.start()

            # Start receiving thread
            self.receive_thread = threading.Thread(
                target=self._receive_loop,
                daemon=True
            )
            self.receive_thread.start()

            self._log_info("Stream receiver started")
            if self.logger:
                self.logger.log_stream_event("STARTED", f"Resolution: {self.width}x{self.height}")

            if self.on_connect:
                self.on_connect()

            return True

        except Exception as e:
            error_msg = f"Error starting stream receiver: {e}"
            self._log_error(error_msg, exc_info=True)
            if self.on_error:
                self.on_error(error_msg)
            return False

    def stop(self) -> None:
        """Stop receiving stream"""
        if not self.running:
            return

        self.running = False

        # Stop FFmpeg process
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._log_warning("FFmpeg did not terminate, killing process")
                self.ffmpeg_process.kill()
            except Exception as e:
                self._log_error(f"Error stopping FFmpeg process: {e}")

        # Wait for threads to finish
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2)

        if self.stderr_thread and self.stderr_thread.is_alive():
            self.stderr_thread.join(timeout=2)

        # Clear queue
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

        self._log_info("Stream receiver stopped")
        if self.logger:
            self.logger.log_stream_event(
                "STOPPED",
                f"Frames: {self.frames_received}, Dropped: {self.frames_dropped}, Errors: {self.connection_errors}"
            )

        if self.on_disconnect:
            self.on_disconnect()

    def _monitor_ffmpeg_errors(self) -> None:
        """Monitor FFmpeg stderr output for errors"""
        while self.running and self.ffmpeg_process:
            try:
                line = self.ffmpeg_process.stderr.readline()
                if not line:
                    break

                line = line.decode('utf-8', errors='ignore').strip()

                # Log important FFmpeg messages
                if 'error' in line.lower():
                    self._log_error(f"FFmpeg error: {line}")
                    if self.logger:
                        self.logger.log_error_event("FFMPEG_ERROR", line, "StreamReceiver")
                elif 'warning' in line.lower():
                    self._log_warning(f"FFmpeg warning: {line}")
                elif 'Connection refused' in line:
                    self.connection_errors += 1
                    self._log_error("FFmpeg: Connection refused - server not reachable")
                    if self.on_error:
                        self.on_error("Connection refused")
                elif 'Packet corrupt' in line or 'corrupt' in line.lower():
                    self._log_warning("FFmpeg: Packet corruption detected")
                elif 'Invalid data' in line:
                    self._log_error("FFmpeg: Invalid stream data")

            except Exception as e:
                if self.running:
                    self._log_error(f"Error monitoring FFmpeg stderr: {e}")
                break

    def _receive_loop(self) -> None:
        """Main loop for receiving frames from FFmpeg with timeout"""
        frame_size = self.width * self.height * 3  # 3 bytes per pixel (BGR)
        consecutive_errors = 0
        max_consecutive_errors = 5

        while self.running:
            try:
                # Check if stream has timed out
                time_since_last_frame = time.time() - self.last_frame_time
                if time_since_last_frame > self.stream_timeout:
                    error_msg = f"Stream timeout - no data received for {time_since_last_frame:.1f} seconds"
                    self._log_error(error_msg)
                    if self.logger:
                        self.logger.log_error_event("STREAM_TIMEOUT", error_msg, "StreamReceiver")
                    if self.on_error:
                        self.on_error("Stream timeout")
                    break

                # Check if FFmpeg process is still running
                if self.ffmpeg_process.poll() is not None:
                    self._log_error("FFmpeg process terminated unexpectedly")
                    if self.logger:
                        self.logger.log_error_event("FFMPEG_DIED", "FFmpeg process died", "StreamReceiver")
                    break

                # Use select on Unix systems for non-blocking read with timeout
                if sys.platform != 'win32':
                    ready = select.select([self.ffmpeg_process.stdout], [], [], 1.0)
                    if not ready[0]:
                        continue  # Timeout, try again

                # Read raw frame data from FFmpeg stdout
                raw_frame = self.ffmpeg_process.stdout.read(frame_size)

                if len(raw_frame) == 0:
                    # EOF reached
                    self._log_warning("FFmpeg stream ended (EOF)")
                    if self.logger:
                        self.logger.log_stream_event("EOF", "Stream ended")
                    break

                if len(raw_frame) != frame_size:
                    # Incomplete frame
                    self.incomplete_frames += 1
                    consecutive_errors += 1

                    self._log_warning(
                        f"Incomplete frame received: {len(raw_frame)}/{frame_size} bytes "
                        f"(error {consecutive_errors}/{max_consecutive_errors})"
                    )

                    if self.logger:
                        self.logger.log_error_event(
                            "INCOMPLETE_FRAME",
                            f"Received {len(raw_frame)}/{frame_size} bytes",
                            "StreamReceiver"
                        )

                    # Too many consecutive errors, bail out
                    if consecutive_errors >= max_consecutive_errors:
                        error_msg = f"Too many consecutive incomplete frames ({consecutive_errors}), stopping"
                        self._log_error(error_msg)
                        if self.on_error:
                            self.on_error(error_msg)
                        break

                    continue

                # Reset error counter on successful frame
                consecutive_errors = 0

                # Convert raw bytes to numpy array
                frame = np.frombuffer(raw_frame, dtype=np.uint8)
                frame = frame.reshape((self.height, self.width, 3))

                # Check queue size and drop frames if necessary
                queue_size = self.frame_queue.qsize()
                if queue_size >= self.frame_drop_threshold:
                    self.frames_dropped += 1
                    self._log_debug(f"Dropping frame, queue size: {queue_size}")
                    continue

                # Add frame to queue
                try:
                    self.frame_queue.put(frame, block=False)
                    self.frames_received += 1
                    self.last_frame_time = time.time()
                except queue.Full:
                    self.frames_dropped += 1
                    self._log_debug("Frame queue full, dropping frame")

            except Exception as e:
                if self.running:
                    error_msg = f"Error receiving frame: {e}"
                    self._log_error(error_msg, exc_info=True)
                    if self.logger:
                        self.logger.log_error_event("RECEIVE_ERROR", str(e), "StreamReceiver")
                    if self.on_error:
                        self.on_error(error_msg)
                break

        self.running = False
        self._log_info("Receive loop ended")

    def get_frame(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """
        Get next frame from queue

        Args:
            timeout: Timeout in seconds

        Returns:
            Frame as numpy array or None if no frame available
        """
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def is_alive(self) -> bool:
        """
        Check if stream is alive

        Returns:
            True if stream is receiving frames, False otherwise
        """
        if not self.running:
            return False

        # Check FFmpeg process is alive
        if self.ffmpeg_process and self.ffmpeg_process.poll() is not None:
            return False

        # Check if we've received frames recently
        time_since_last_frame = time.time() - self.last_frame_time
        if time_since_last_frame > self.stream_timeout * 2:  # Double timeout for is_alive check
            self._log_warning(f"Stream appears dead - no frames for {time_since_last_frame:.1f}s")
            return False

        return True

    def get_stats(self) -> dict:
        """
        Get receiver statistics

        Returns:
            Dictionary with statistics
        """
        time_since_last_frame = time.time() - self.last_frame_time if self.running else 0

        return {
            'frames_received': self.frames_received,
            'frames_dropped': self.frames_dropped,
            'incomplete_frames': self.incomplete_frames,
            'connection_errors': self.connection_errors,
            'queue_size': self.frame_queue.qsize(),
            'is_alive': self.is_alive(),
            'running': self.running,
            'time_since_last_frame': time_since_last_frame
        }

    def _log_debug(self, message: str):
        """Log debug message"""
        if self.logger:
            self.logger.debug(message, "StreamReceiver")
        else:
            logging.debug(f"[StreamReceiver] {message}")

    def _log_info(self, message: str):
        """Log info message"""
        if self.logger:
            self.logger.info(message, "StreamReceiver")
        else:
            logging.info(f"[StreamReceiver] {message}")

    def _log_warning(self, message: str):
        """Log warning message"""
        if self.logger:
            self.logger.warning(message, "StreamReceiver")
        else:
            logging.warning(f"[StreamReceiver] {message}")

    def _log_error(self, message: str, exc_info: bool = False):
        """Log error message"""
        if self.logger:
            self.logger.error(message, "StreamReceiver", exc_info=exc_info)
        else:
            logging.error(f"[StreamReceiver] {message}", exc_info=exc_info)

    def __del__(self):
        """Cleanup on deletion"""
        self.stop()
