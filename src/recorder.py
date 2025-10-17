"""
Recorder for RTP Video Streaming Client
Handles recording video frames to file
"""

import cv2
import os
import logging
import time
from datetime import datetime
from typing import Optional
import numpy as np


class Recorder:
    """Records video frames to file using OpenCV VideoWriter"""

    def __init__(self, output_dir: str, filename_pattern: str,
                 format: str = "mp4", codec: str = "h264", fps: int = 30):
        """
        Initialize recorder

        Args:
            output_dir: Output directory for recordings
            filename_pattern: Filename pattern with datetime format
            format: Output format (mp4, avi, mkv)
            codec: Video codec (h264, xvid, etc.)
            fps: Frames per second for recording
        """
        self.output_dir = output_dir
        self.filename_pattern = filename_pattern
        self.format = format
        self.codec = codec
        self.fps = fps

        # Recording state
        self.is_recording = False
        self.video_writer: Optional[cv2.VideoWriter] = None
        self.current_filename: Optional[str] = None
        self.frame_count = 0
        self.start_time: Optional[float] = None

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
            logging.warning("Already recording")
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
            self.start_time = time.time()

            logging.info(f"Started recording to: {self.current_filename}")
            return True

        except Exception as e:
            logging.error(f"Error starting recording: {e}")
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
            logging.warning("Not currently recording")
            return None

        try:
            # Release video writer
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None

            self.is_recording = False

            # Calculate statistics
            duration = time.time() - self.start_time if self.start_time else 0
            file_size = os.path.getsize(self.current_filename) if self.current_filename else 0

            logging.info(
                f"Recording stopped: {self.current_filename} "
                f"({self.frame_count} frames, {duration:.2f}s, {file_size / 1024 / 1024:.2f} MB)"
            )

            filename = self.current_filename
            self.current_filename = None
            self.frame_count = 0
            self.start_time = None

            return filename

        except Exception as e:
            logging.error(f"Error stopping recording: {e}")
            return None

    def write_frame(self, frame: np.ndarray) -> bool:
        """
        Write frame to video

        Args:
            frame: Frame as numpy array (BGR format)

        Returns:
            True if frame written successfully, False otherwise
        """
        if not self.is_recording or not self.video_writer:
            return False

        try:
            self.video_writer.write(frame)
            self.frame_count += 1
            return True

        except Exception as e:
            logging.error(f"Error writing frame: {e}")
            return False

    def get_status(self) -> dict:
        """
        Get recording status

        Returns:
            Dictionary with recording status
        """
        duration = time.time() - self.start_time if self.start_time and self.is_recording else 0

        return {
            'is_recording': self.is_recording,
            'filename': self.current_filename,
            'frame_count': self.frame_count,
            'duration': duration,
            'fps': self.fps
        }

    def __del__(self):
        """Cleanup on deletion"""
        if self.is_recording:
            self.stop_recording()
