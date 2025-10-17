"""
Snapshot Manager for RTP Video Streaming Client
Handles capturing and saving snapshots from video stream
"""

import cv2
import os
import logging
from datetime import datetime
from typing import Optional
import numpy as np


class SnapshotManager:
    """Manages capturing and saving video snapshots"""

    def __init__(self, output_dir: str, filename_pattern: str,
                 format: str = "jpg", quality: int = 95):
        """
        Initialize snapshot manager

        Args:
            output_dir: Output directory for snapshots
            filename_pattern: Filename pattern with datetime format
            format: Image format (jpg, png)
            quality: JPEG quality (0-100) or PNG compression (0-9)
        """
        self.output_dir = output_dir
        self.filename_pattern = filename_pattern
        self.format = format.lower()
        self.quality = quality

        # Statistics
        self.snapshots_taken = 0
        self.last_snapshot_path: Optional[str] = None

    def capture_snapshot(self, frame: np.ndarray) -> Optional[str]:
        """
        Capture and save snapshot from frame

        Args:
            frame: Frame as numpy array (BGR format)

        Returns:
            Path to saved snapshot file or None if failed
        """
        if frame is None or frame.size == 0:
            logging.warning("Cannot capture snapshot: invalid frame")
            return None

        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime(self.filename_pattern)
            filename = os.path.join(
                self.output_dir,
                f"{timestamp}.{self.format}"
            )

            # Set encoding parameters based on format
            if self.format == 'jpg' or self.format == 'jpeg':
                params = [cv2.IMWRITE_JPEG_QUALITY, self.quality]
            elif self.format == 'png':
                # PNG compression level (0-9, where 9 is max compression)
                compression = int((100 - self.quality) / 100 * 9)
                params = [cv2.IMWRITE_PNG_COMPRESSION, compression]
            else:
                params = []

            # Save image
            success = cv2.imwrite(filename, frame, params)

            if success:
                self.snapshots_taken += 1
                self.last_snapshot_path = filename
                file_size = os.path.getsize(filename)
                logging.info(
                    f"Snapshot saved: {filename} "
                    f"({frame.shape[1]}x{frame.shape[0]}, {file_size / 1024:.2f} KB)"
                )
                return filename
            else:
                logging.error(f"Failed to save snapshot to {filename}")
                return None

        except Exception as e:
            logging.error(f"Error capturing snapshot: {e}")
            return None

    def get_stats(self) -> dict:
        """
        Get snapshot statistics

        Returns:
            Dictionary with snapshot statistics
        """
        return {
            'snapshots_taken': self.snapshots_taken,
            'last_snapshot': self.last_snapshot_path,
            'output_dir': self.output_dir,
            'format': self.format
        }
