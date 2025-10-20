"""
Connection Manager for RTP Video Streaming Client
Handles connection with auto-reconnect and health monitoring
"""

import time
import threading
from typing import Optional, Callable


class ConnectionManager:
    """Manages stream connection with automatic reconnection"""

    def __init__(self, stream_receiver, config, logger=None,
                 auto_reconnect: bool = True,
                 max_reconnect_attempts: int = 0,
                 reconnect_interval: float = 5.0,
                 health_check_interval: float = 2.0):
        """
        Initialize connection manager

        Args:
            stream_receiver: StreamReceiver instance
            config: ConfigManager instance
            logger: Application logger
            auto_reconnect: Enable automatic reconnection
            max_reconnect_attempts: Maximum reconnection attempts (0 = infinite)
            reconnect_interval: Seconds between reconnection attempts
            health_check_interval: Seconds between health checks
        """
        self.stream_receiver = stream_receiver
        self.config = config
        self.logger = logger
        self.auto_reconnect = auto_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_interval = reconnect_interval
        self.health_check_interval = health_check_interval

        # State
        self.is_connected = False
        self.is_reconnecting = False
        self.reconnect_count = 0
        self.last_disconnect_time: Optional[float] = None

        # Health monitoring
        self.health_check_thread: Optional[threading.Thread] = None
        self.monitoring = False

        # Callbacks
        self.on_connect_success: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None
        self.on_reconnect_failed: Optional[Callable] = None

    def connect(self) -> bool:
        """
        Connect to stream

        Returns:
            True if connected successfully, False otherwise
        """
        if self.is_connected:
            self._log_warning("Already connected")
            return True

        try:
            # Attempt connection
            if self.stream_receiver.start():
                self.is_connected = True
                self.reconnect_count = 0
                self._log_info("Connection established")

                if self.logger:
                    self.logger.log_connection_event(True, "Initial connection")

                # Start health monitoring
                if self.auto_reconnect:
                    self._start_health_monitoring()

                # Trigger callback
                if self.on_connect_success:
                    self.on_connect_success()

                return True
            else:
                self._log_error("Connection failed")
                return False

        except Exception as e:
            self._log_error(f"Connection error: {e}", exc_info=True)
            return False

    def disconnect(self) -> None:
        """Disconnect from stream"""
        if not self.is_connected:
            return

        try:
            # Stop health monitoring
            self._stop_health_monitoring()

            # Disconnect stream
            self.stream_receiver.stop()

            self.is_connected = False
            self.last_disconnect_time = time.time()

            self._log_info("Disconnected")

            if self.logger:
                self.logger.log_connection_event(False, "Manual disconnect")

            # Trigger callback
            if self.on_disconnect:
                self.on_disconnect()

        except Exception as e:
            self._log_error(f"Disconnect error: {e}", exc_info=True)

    def _reconnect(self) -> bool:
        """
        Attempt to reconnect

        Returns:
            True if reconnected successfully, False otherwise
        """
        if self.is_reconnecting:
            return False

        self.is_reconnecting = True
        success = False

        try:
            self.reconnect_count += 1

            self._log_info(
                f"Reconnection attempt {self.reconnect_count}"
                f"{f'/{self.max_reconnect_attempts}' if self.max_reconnect_attempts > 0 else ''}"
            )

            if self.logger:
                self.logger.event(
                    "RECONNECT",
                    f"Attempt {self.reconnect_count}",
                    "ConnectionManager"
                )

            # Wait before reconnecting
            time.sleep(self.reconnect_interval)

            # Stop previous connection
            if self.stream_receiver.running:
                self.stream_receiver.stop()

            # Attempt new connection
            if self.stream_receiver.start():
                self.is_connected = True
                self.reconnect_count = 0
                success = True

                self._log_info("Reconnection successful")

                if self.logger:
                    self.logger.log_connection_event(True, "Reconnection successful")

                # Trigger callback
                if self.on_connect_success:
                    self.on_connect_success()
            else:
                self._log_warning("Reconnection failed")

        except Exception as e:
            self._log_error(f"Reconnection error: {e}", exc_info=True)

        finally:
            self.is_reconnecting = False

        # Check if max attempts reached
        if not success:
            if self.max_reconnect_attempts > 0 and self.reconnect_count >= self.max_reconnect_attempts:
                self._log_error(f"Maximum reconnection attempts ({self.max_reconnect_attempts}) reached")

                if self.logger:
                    self.logger.log_error_event(
                        "RECONNECT_FAILED",
                        f"Max attempts ({self.max_reconnect_attempts}) reached",
                        "ConnectionManager"
                    )

                # Trigger callback
                if self.on_reconnect_failed:
                    self.on_reconnect_failed()

                return False

        return success

    def _start_health_monitoring(self) -> None:
        """Start health monitoring thread"""
        if self.monitoring:
            return

        self.monitoring = True
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self.health_check_thread.start()

        self._log_info("Health monitoring started")

    def _stop_health_monitoring(self) -> None:
        """Stop health monitoring thread"""
        if not self.monitoring:
            return

        self.monitoring = False

        if self.health_check_thread and self.health_check_thread.is_alive():
            self.health_check_thread.join(timeout=2)

        self._log_info("Health monitoring stopped")

    def _health_check_loop(self) -> None:
        """Health monitoring loop"""
        while self.monitoring and self.is_connected:
            try:
                time.sleep(self.health_check_interval)

                # Check if stream is alive
                if not self.stream_receiver.is_alive():
                    self._log_warning("Stream health check failed - connection appears dead")

                    if self.logger:
                        self.logger.log_error_event(
                            "STREAM_DEAD",
                            "Health check failed",
                            "ConnectionManager"
                        )

                    # Mark as disconnected
                    self.is_connected = False
                    self.last_disconnect_time = time.time()

                    # Trigger disconnect callback
                    if self.on_disconnect:
                        self.on_disconnect()

                    # Attempt reconnection if enabled
                    if self.auto_reconnect:
                        if not self._check_max_attempts():
                            self._reconnect()
                    else:
                        break

            except Exception as e:
                self._log_error(f"Health check error: {e}", exc_info=True)

        self._log_info("Health check loop ended")

    def _check_max_attempts(self) -> bool:
        """
        Check if maximum reconnection attempts reached

        Returns:
            True if max attempts reached, False otherwise
        """
        if self.max_reconnect_attempts > 0 and self.reconnect_count >= self.max_reconnect_attempts:
            return True
        return False

    def get_status(self) -> dict:
        """
        Get connection status

        Returns:
            Dictionary with connection status
        """
        return {
            'is_connected': self.is_connected,
            'is_reconnecting': self.is_reconnecting,
            'reconnect_count': self.reconnect_count,
            'auto_reconnect': self.auto_reconnect,
            'max_attempts': self.max_reconnect_attempts,
            'monitoring': self.monitoring
        }

    def _log_info(self, message: str):
        """Log info message"""
        if self.logger:
            self.logger.info(message, "ConnectionManager")

    def _log_warning(self, message: str):
        """Log warning message"""
        if self.logger:
            self.logger.warning(message, "ConnectionManager")

    def _log_error(self, message: str, exc_info: bool = False):
        """Log error message"""
        if self.logger:
            self.logger.error(message, "ConnectionManager", exc_info=exc_info)
