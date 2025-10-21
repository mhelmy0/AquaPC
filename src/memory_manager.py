"""
Memory Manager Module
Handles dynamic buffer sizing based on available system RAM
"""

import psutil
from typing import Dict, Optional, Tuple
import logging


class MemoryManager:
    """
    Manages memory allocation for video streaming buffers.
    Dynamically calculates optimal buffer sizes based on available RAM.
    """

    def __init__(self,
                 max_ram_usage_percent: int = 70,
                 frame_width: int = 1920,
                 frame_height: int = 1080,
                 logger=None):
        """
        Initialize Memory Manager.

        Args:
            max_ram_usage_percent: Maximum percentage of free RAM to use (default: 70%)
            frame_width: Width of video frame in pixels
            frame_height: Height of video frame in pixels
            logger: Optional logger instance
        """
        self.max_ram_usage_percent = max_ram_usage_percent
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.logger = logger

        # Calculate size of a single frame in bytes (RGB: 3 bytes per pixel)
        self.frame_size_bytes = frame_width * frame_height * 3

        # Minimum buffer sizes (safety limits)
        self.MIN_FRAME_BUFFER = 100
        self.MIN_RECORDING_BUFFER = 50
        self.MIN_UDP_BUFFER = 65536  # 64KB

        # Maximum buffer sizes (safety limits to prevent excessive RAM usage)
        self.MAX_FRAME_BUFFER = 10000
        self.MAX_RECORDING_BUFFER = 5000
        self.MAX_UDP_BUFFER = 67108864  # 64MB

        self._log_info("MemoryManager initialized")
        self._log_info(f"Frame size: {self.frame_size_bytes / (1024**2):.2f} MB ({frame_width}x{frame_height})")
        self._log_info(f"Max RAM usage: {max_ram_usage_percent}%")

    def get_system_memory_info(self) -> Dict[str, float]:
        """
        Get current system memory information.

        Returns:
            Dictionary with memory stats in MB:
            - total: Total system RAM
            - available: Available RAM
            - used: Used RAM
            - percent: Percentage used
            - free: Free RAM
        """
        mem = psutil.virtual_memory()

        info = {
            'total_mb': mem.total / (1024**2),
            'available_mb': mem.available / (1024**2),
            'used_mb': mem.used / (1024**2),
            'percent': mem.percent,
            'free_mb': mem.free / (1024**2)
        }

        return info

    def calculate_optimal_buffers(self) -> Dict[str, int]:
        """
        Calculate optimal buffer sizes based on available system RAM.

        Returns:
            Dictionary with calculated buffer sizes:
            - frame_buffer_size: Number of frames for main buffer
            - recording_queue_size: Number of frames for recording queue
            - udp_buffer_size: UDP receive buffer size in bytes
            - total_memory_mb: Total memory that will be used
        """
        mem_info = self.get_system_memory_info()
        available_mb = mem_info['available_mb']

        # Calculate how much RAM we can use (70% of available)
        usable_ram_mb = available_mb * (self.max_ram_usage_percent / 100.0)
        usable_ram_bytes = usable_ram_mb * (1024**2)

        self._log_info(f"System RAM - Total: {mem_info['total_mb']:.0f} MB, "
                      f"Available: {available_mb:.0f} MB, "
                      f"Used: {mem_info['percent']:.1f}%")
        self._log_info(f"Usable RAM for buffers: {usable_ram_mb:.0f} MB ({self.max_ram_usage_percent}%)")

        # Allocate RAM across different buffers
        # Distribution: 60% for main frame buffer, 30% for recording queue, 10% for UDP buffer

        # 1. Main frame buffer (60% of usable RAM)
        frame_buffer_bytes = usable_ram_bytes * 0.60
        frame_buffer_size = int(frame_buffer_bytes / self.frame_size_bytes)
        frame_buffer_size = max(self.MIN_FRAME_BUFFER, min(frame_buffer_size, self.MAX_FRAME_BUFFER))

        # 2. Recording queue (30% of usable RAM)
        recording_buffer_bytes = usable_ram_bytes * 0.30
        recording_queue_size = int(recording_buffer_bytes / self.frame_size_bytes)
        recording_queue_size = max(self.MIN_RECORDING_BUFFER, min(recording_queue_size, self.MAX_RECORDING_BUFFER))

        # 3. UDP buffer (10% of usable RAM, but capped at reasonable max)
        udp_buffer_size = int(usable_ram_bytes * 0.10)
        udp_buffer_size = max(self.MIN_UDP_BUFFER, min(udp_buffer_size, self.MAX_UDP_BUFFER))

        # Calculate actual memory usage
        actual_frame_buffer_mb = (frame_buffer_size * self.frame_size_bytes) / (1024**2)
        actual_recording_buffer_mb = (recording_queue_size * self.frame_size_bytes) / (1024**2)
        actual_udp_buffer_mb = udp_buffer_size / (1024**2)
        total_memory_mb = actual_frame_buffer_mb + actual_recording_buffer_mb + actual_udp_buffer_mb

        buffers = {
            'frame_buffer_size': frame_buffer_size,
            'recording_queue_size': recording_queue_size,
            'udp_buffer_size': udp_buffer_size,
            'total_memory_mb': total_memory_mb
        }

        self._log_info("Calculated optimal buffer sizes:")
        self._log_info(f"  Frame buffer: {frame_buffer_size} frames ({actual_frame_buffer_mb:.1f} MB)")
        self._log_info(f"  Recording queue: {recording_queue_size} frames ({actual_recording_buffer_mb:.1f} MB)")
        self._log_info(f"  UDP buffer: {udp_buffer_size} bytes ({actual_udp_buffer_mb:.1f} MB)")
        self._log_info(f"  Total memory allocation: {total_memory_mb:.1f} MB")
        self._log_info(f"  Percentage of available RAM: {(total_memory_mb / available_mb) * 100:.1f}%")

        return buffers

    def get_buffer_stats(self, current_frame_count: int, current_recording_count: int) -> Dict[str, float]:
        """
        Get current buffer utilization statistics.

        Args:
            current_frame_count: Current number of frames in main buffer
            current_recording_count: Current number of frames in recording queue

        Returns:
            Dictionary with buffer stats
        """
        frame_buffer_mb = (current_frame_count * self.frame_size_bytes) / (1024**2)
        recording_buffer_mb = (current_recording_count * self.frame_size_bytes) / (1024**2)
        total_buffer_mb = frame_buffer_mb + recording_buffer_mb

        mem_info = self.get_system_memory_info()

        stats = {
            'frame_buffer_mb': frame_buffer_mb,
            'recording_buffer_mb': recording_buffer_mb,
            'total_buffer_mb': total_buffer_mb,
            'system_available_mb': mem_info['available_mb'],
            'system_percent_used': mem_info['percent']
        }

        return stats

    def check_memory_health(self) -> Tuple[bool, str]:
        """
        Check if system has healthy memory levels.

        Returns:
            Tuple of (is_healthy, message)
        """
        mem_info = self.get_system_memory_info()

        # Critical if less than 500MB available
        if mem_info['available_mb'] < 500:
            return False, f"CRITICAL: Low memory! Only {mem_info['available_mb']:.0f} MB available"

        # Warning if less than 1GB available
        elif mem_info['available_mb'] < 1024:
            return True, f"WARNING: Low memory. {mem_info['available_mb']:.0f} MB available"

        # Healthy
        else:
            return True, f"Memory OK. {mem_info['available_mb']:.0f} MB available"

    def _log_info(self, message: str) -> None:
        """Log info message"""
        if self.logger:
            self.logger.info(message, "MemoryManager")
        else:
            logging.info(f"MemoryManager: {message}")

    def _log_warning(self, message: str) -> None:
        """Log warning message"""
        if self.logger:
            self.logger.warning(message, "MemoryManager")
        else:
            logging.warning(f"MemoryManager: {message}")

    def _log_error(self, message: str) -> None:
        """Log error message"""
        if self.logger:
            self.logger.error(message, "MemoryManager")
        else:
            logging.error(f"MemoryManager: {message}")


def get_optimal_buffers(frame_width: int = 1920,
                       frame_height: int = 1080,
                       max_ram_percent: int = 70,
                       logger=None) -> Dict[str, int]:
    """
    Convenience function to get optimal buffer sizes.

    Args:
        frame_width: Video frame width
        frame_height: Video frame height
        max_ram_percent: Maximum percentage of free RAM to use
        logger: Optional logger instance

    Returns:
        Dictionary with optimal buffer sizes
    """
    manager = MemoryManager(
        max_ram_usage_percent=max_ram_percent,
        frame_width=frame_width,
        frame_height=frame_height,
        logger=logger
    )

    return manager.calculate_optimal_buffers()
