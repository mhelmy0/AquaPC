"""
Stream Receiver for RTP Video Streaming Client
Handles receiving and decoding RTP H.264 video stream using FFmpeg
"""

import subprocess
import threading
import queue
import logging
import time
import numpy as np
from typing import Optional, Callable


class StreamReceiver:
    """Receives and decodes RTP video stream using FFmpeg subprocess"""

    def __init__(self, ffmpeg_cmd: list, width: int, height: int,
                 buffer_size: int = 10, frame_drop_threshold: int = 10):
        """
        Initialize stream receiver

        Args:
            ffmpeg_cmd: FFmpeg command as list of arguments
            width: Video frame width
            height: Video frame height
            buffer_size: Maximum frame buffer size
            frame_drop_threshold: Drop frames if queue exceeds this size
        """
        self.ffmpeg_cmd = ffmpeg_cmd
        self.width = width
        self.height = height
        self.buffer_size = buffer_size
        self.frame_drop_threshold = frame_drop_threshold

        # Frame buffer queue
        self.frame_queue = queue.Queue(maxsize=buffer_size)

        # Threading
        self.receive_thread: Optional[threading.Thread] = None
        self.running = False

        # FFmpeg process
        self.ffmpeg_process: Optional[subprocess.Popen] = None

        # Statistics
        self.frames_received = 0
        self.frames_dropped = 0
        self.last_frame_time = time.time()

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
            logging.warning("Stream receiver already running")
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

            # Start receiving thread
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()

            logging.info("Stream receiver started")

            if self.on_connect:
                self.on_connect()

            return True

        except Exception as e:
            error_msg = f"Error starting stream receiver: {e}"
            logging.error(error_msg)
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
                self.ffmpeg_process.kill()
            except Exception as e:
                logging.error(f"Error stopping FFmpeg process: {e}")

        # Wait for thread to finish
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2)

        # Clear queue
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

        logging.info("Stream receiver stopped")

        if self.on_disconnect:
            self.on_disconnect()

    def _receive_loop(self) -> None:
        """Main loop for receiving frames from FFmpeg"""
        frame_size = self.width * self.height * 3  # 3 bytes per pixel (BGR)

        while self.running:
            try:
                # Read raw frame data from FFmpeg stdout
                raw_frame = self.ffmpeg_process.stdout.read(frame_size)

                if len(raw_frame) != frame_size:
                    # End of stream or error
                    logging.warning("Incomplete frame received, stream may have ended")
                    break

                # Convert raw bytes to numpy array
                frame = np.frombuffer(raw_frame, dtype=np.uint8)
                frame = frame.reshape((self.height, self.width, 3))

                # Check queue size and drop frames if necessary
                queue_size = self.frame_queue.qsize()
                if queue_size >= self.frame_drop_threshold:
                    self.frames_dropped += 1
                    logging.debug(f"Dropping frame, queue size: {queue_size}")
                    continue

                # Add frame to queue
                try:
                    self.frame_queue.put(frame, block=False)
                    self.frames_received += 1
                    self.last_frame_time = time.time()
                except queue.Full:
                    self.frames_dropped += 1
                    logging.debug("Frame queue full, dropping frame")

            except Exception as e:
                if self.running:
                    error_msg = f"Error receiving frame: {e}"
                    logging.error(error_msg)
                    if self.on_error:
                        self.on_error(error_msg)
                break

        self.running = False

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

        # Check if we've received a frame recently (within 5 seconds)
        time_since_last_frame = time.time() - self.last_frame_time
        return time_since_last_frame < 5.0

    def get_stats(self) -> dict:
        """
        Get receiver statistics

        Returns:
            Dictionary with statistics
        """
        return {
            'frames_received': self.frames_received,
            'frames_dropped': self.frames_dropped,
            'queue_size': self.frame_queue.qsize(),
            'is_alive': self.is_alive(),
            'running': self.running
        }

    def __del__(self):
        """Cleanup on deletion"""
        self.stop()
