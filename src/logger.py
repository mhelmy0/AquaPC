"""
Logging Module for RTP Video Streaming Client
Provides centralized logging with separate files for errors, warnings, and events
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional


class AppLogger:
    """Centralized application logger with multiple log files"""

    def __init__(self, log_dir: str = "logs", log_level: str = "INFO"):
        """
        Initialize application logger

        Args:
            log_dir: Directory for log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.log_dir = log_dir
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)

        # Create log directory if it doesn't exist
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)

        # Initialize loggers
        self.main_logger = self._setup_logger('main', 'app.log', self.log_level)
        self.error_logger = self._setup_logger('error', 'errors.log', logging.ERROR)
        self.warning_logger = self._setup_logger('warning', 'warnings.log', logging.WARNING)
        self.event_logger = self._setup_logger('event', 'events.log', logging.INFO)

    def _setup_logger(self, name: str, filename: str, level: int) -> logging.Logger:
        """
        Setup a logger with rotating file handler

        Args:
            name: Logger name
            filename: Log file name
            level: Minimum logging level

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Prevent duplicate handlers
        if logger.handlers:
            return logger

        # File path
        log_path = os.path.join(self.log_dir, filename)

        # Create rotating file handler (10 MB per file, keep 5 backups)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setLevel(level)

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def debug(self, message: str, component: Optional[str] = None):
        """
        Log debug message

        Args:
            message: Log message
            component: Optional component name
        """
        if component:
            message = f"[{component}] {message}"
        self.main_logger.debug(message)

    def info(self, message: str, component: Optional[str] = None):
        """
        Log info message

        Args:
            message: Log message
            component: Optional component name
        """
        if component:
            message = f"[{component}] {message}"
        self.main_logger.info(message)

    def warning(self, message: str, component: Optional[str] = None):
        """
        Log warning message (goes to both main and warning log)

        Args:
            message: Log message
            component: Optional component name
        """
        if component:
            message = f"[{component}] {message}"
        self.main_logger.warning(message)
        self.warning_logger.warning(message)

    def error(self, message: str, component: Optional[str] = None, exc_info: bool = False):
        """
        Log error message (goes to both main and error log)

        Args:
            message: Log message
            component: Optional component name
            exc_info: Include exception traceback
        """
        if component:
            message = f"[{component}] {message}"
        self.main_logger.error(message, exc_info=exc_info)
        self.error_logger.error(message, exc_info=exc_info)

    def critical(self, message: str, component: Optional[str] = None, exc_info: bool = False):
        """
        Log critical message

        Args:
            message: Log message
            component: Optional component name
            exc_info: Include exception traceback
        """
        if component:
            message = f"[{component}] {message}"
        self.main_logger.critical(message, exc_info=exc_info)
        self.error_logger.critical(message, exc_info=exc_info)

    def event(self, event_type: str, message: str, component: Optional[str] = None):
        """
        Log application event (goes to event log)

        Args:
            event_type: Type of event (CONNECT, DISCONNECT, RECORD_START, etc.)
            message: Event description
            component: Optional component name
        """
        if component:
            message = f"[{component}] [{event_type}] {message}"
        else:
            message = f"[{event_type}] {message}"
        self.event_logger.info(message)
        self.main_logger.info(message)

    def log_stream_event(self, event: str, details: str = ""):
        """
        Log stream-related event

        Args:
            event: Event name (CONNECT, DISCONNECT, FRAME_RECEIVED, etc.)
            details: Additional details
        """
        message = f"Stream {event}"
        if details:
            message += f" - {details}"
        self.event("STREAM", message, "StreamReceiver")

    def log_recording_event(self, event: str, details: str = ""):
        """
        Log recording-related event

        Args:
            event: Event name (START, STOP, FRAME_WRITTEN, etc.)
            details: Additional details
        """
        message = f"Recording {event}"
        if details:
            message += f" - {details}"
        self.event("RECORDING", message, "Recorder")

    def log_snapshot_event(self, details: str = ""):
        """
        Log snapshot capture event

        Args:
            details: Snapshot details (filename, size, etc.)
        """
        message = f"Snapshot captured"
        if details:
            message += f" - {details}"
        self.event("SNAPSHOT", message, "SnapshotManager")

    def log_connection_event(self, connected: bool, details: str = ""):
        """
        Log connection status change

        Args:
            connected: True if connected, False if disconnected
            details: Additional details
        """
        status = "CONNECTED" if connected else "DISCONNECTED"
        message = f"Stream connection {status}"
        if details:
            message += f" - {details}"
        self.event("CONNECTION", message)

    def log_error_event(self, error_type: str, error_msg: str, component: Optional[str] = None):
        """
        Log error with event tracking

        Args:
            error_type: Type of error
            error_msg: Error message
            component: Component where error occurred
        """
        message = f"{error_type}: {error_msg}"
        self.error(message, component, exc_info=True)
        self.event("ERROR", message, component)

    def get_log_stats(self) -> dict:
        """
        Get logging statistics

        Returns:
            Dictionary with log file information
        """
        stats = {}
        log_files = ['app.log', 'errors.log', 'warnings.log', 'events.log']

        for log_file in log_files:
            log_path = os.path.join(self.log_dir, log_file)
            if os.path.exists(log_path):
                stats[log_file] = {
                    'path': log_path,
                    'size': os.path.getsize(log_path),
                    'modified': datetime.fromtimestamp(os.path.getmtime(log_path))
                }
            else:
                stats[log_file] = None

        return stats


# Global logger instance
_logger_instance: Optional[AppLogger] = None


def get_logger(log_dir: str = "logs", log_level: str = "INFO") -> AppLogger:
    """
    Get or create global logger instance

    Args:
        log_dir: Directory for log files
        log_level: Logging level

    Returns:
        AppLogger instance
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = AppLogger(log_dir, log_level)
    return _logger_instance


def setup_logger(log_dir: str = "logs", log_level: str = "INFO") -> AppLogger:
    """
    Setup and return logger instance

    Args:
        log_dir: Directory for log files
        log_level: Logging level

    Returns:
        AppLogger instance
    """
    global _logger_instance
    _logger_instance = AppLogger(log_dir, log_level)
    return _logger_instance
