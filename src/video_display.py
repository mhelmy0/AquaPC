"""
Video Display GUI for RTP Video Streaming Client
Main application window with PyQt5
"""

import sys
import logging
import time
import numpy as np
from typing import Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStatusBar, QMessageBox
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap

from .config import ConfigManager
from .stream_receiver import StreamReceiver
from .recorder import Recorder
from .snapshot import SnapshotManager


class VideoStreamApp(QMainWindow):
    """Main application window for video streaming client"""

    def __init__(self, config: ConfigManager):
        """
        Initialize application

        Args:
            config: Configuration manager instance
        """
        super().__init__()
        self.config = config

        # Components
        self.stream_receiver: Optional[StreamReceiver] = None
        self.recorder: Optional[Recorder] = None
        self.snapshot_manager: Optional[SnapshotManager] = None

        # State
        self.current_frame: Optional[np.ndarray] = None
        self.is_connected = False

        # Statistics
        self.fps_counter = 0
        self.fps_last_time = time.time()
        self.current_fps = 0.0

        # Initialize UI
        self.init_ui()

        # Initialize components
        self.init_components()

        # Setup timers
        self.setup_timers()

    def init_ui(self):
        """Initialize user interface"""
        # Window settings
        title = self.config.get('display', 'window_title', 'Video Stream')
        self.setWindowTitle(title)

        width = self.config.get('display', 'width', 1280)
        height = self.config.get('display', 'height', 720)

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Video display label
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(width, height)
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setText("No Stream")
        layout.addWidget(self.video_label)

        # Info label (FPS, status)
        self.info_label = QLabel("Status: Disconnected")
        self.info_label.setAlignment(Qt.AlignLeft)
        self.info_label.setStyleSheet("padding: 5px; font-family: monospace;")
        layout.addWidget(self.info_label)

        # Control buttons
        button_layout = QHBoxLayout()

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        button_layout.addWidget(self.connect_button)

        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setEnabled(False)
        button_layout.addWidget(self.record_button)

        self.snapshot_button = QPushButton("Take Snapshot")
        self.snapshot_button.clicked.connect(self.take_snapshot)
        self.snapshot_button.setEnabled(False)
        button_layout.addWidget(self.snapshot_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Adjust window size
        self.adjustSize()

    def init_components(self):
        """Initialize stream receiver, recorder, and snapshot manager"""
        # Initialize recorder with auto-calculated buffer sizes
        recording_config = self.config.get_section('recording')
        recording_queue_size = self.config.get_recording_queue_size()  # Uses auto-calculated or config value
        self.recorder = Recorder(
            output_dir=recording_config.get('output_dir', './recordings'),
            filename_pattern=recording_config.get('filename_pattern', 'recording_%Y%m%d_%H%M%S'),
            format=recording_config.get('format', 'mp4'),
            codec=recording_config.get('codec', 'h264'),
            fps=recording_config.get('fps', 30),
            async_write=self.config.get('advanced', 'recording_async', True),
            write_queue_size=recording_queue_size
        )

        # Initialize snapshot manager
        snapshot_config = self.config.get_section('snapshot')
        self.snapshot_manager = SnapshotManager(
            output_dir=snapshot_config.get('output_dir', './snapshots'),
            filename_pattern=snapshot_config.get('filename_pattern', 'snapshot_%Y%m%d_%H%M%S'),
            format=snapshot_config.get('format', 'jpg'),
            quality=snapshot_config.get('quality', 95)
        )

    def setup_timers(self):
        """Setup timers for frame updates and statistics"""
        # Frame update timer (30 FPS = ~33ms)
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self.update_frame)

        # Statistics update timer (1 second)
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_statistics)
        self.stats_timer.start(1000)

    def toggle_connection(self):
        """Toggle stream connection"""
        if self.is_connected:
            self.disconnect_stream()
        else:
            self.connect_stream()

    def connect_stream(self):
        """Connect to stream"""
        try:
            # Get stream parameters
            width = self.config.get('display', 'width', 1280)
            height = self.config.get('display', 'height', 720)
            buffer_size = self.config.get_buffer_size()  # Uses auto-calculated or config value
            frame_drop_threshold = self.config.get('advanced', 'frame_drop_threshold', 10)

            # Build FFmpeg command (uses auto-calculated UDP buffer if enabled)
            ffmpeg_cmd = self.config.get_ffmpeg_command()

            # Create stream receiver
            self.stream_receiver = StreamReceiver(
                ffmpeg_cmd=ffmpeg_cmd,
                width=width,
                height=height,
                buffer_size=buffer_size,
                frame_drop_threshold=frame_drop_threshold
            )

            # Set callbacks
            self.stream_receiver.on_connect = self.on_stream_connected
            self.stream_receiver.on_disconnect = self.on_stream_disconnected
            self.stream_receiver.on_error = self.on_stream_error

            # Start stream
            if self.stream_receiver.start():
                self.frame_timer.start(33)  # ~30 FPS
                self.connect_button.setText("Disconnect")
                self.status_bar.showMessage("Connecting...")
            else:
                QMessageBox.critical(self, "Error", "Failed to connect to stream")

        except Exception as e:
            logging.error(f"Error connecting to stream: {e}")
            QMessageBox.critical(self, "Error", f"Connection error: {e}")

    def disconnect_stream(self):
        """Disconnect from stream"""
        # Stop recording if active
        if self.recorder and self.recorder.is_recording:
            self.toggle_recording()

        # Stop stream
        if self.stream_receiver:
            self.stream_receiver.stop()
            self.stream_receiver = None

        self.frame_timer.stop()
        self.is_connected = False
        self.connect_button.setText("Connect")
        self.record_button.setEnabled(False)
        self.snapshot_button.setEnabled(False)
        self.video_label.setText("No Stream")
        self.status_bar.showMessage("Disconnected")

    def on_stream_connected(self):
        """Callback when stream connects"""
        self.is_connected = True
        self.record_button.setEnabled(True)
        self.snapshot_button.setEnabled(True)
        self.status_bar.showMessage("Connected")
        logging.info("Stream connected")

    def on_stream_disconnected(self):
        """Callback when stream disconnects"""
        self.is_connected = False
        self.status_bar.showMessage("Stream disconnected")
        logging.info("Stream disconnected")

    def on_stream_error(self, error_msg: str):
        """Callback when stream error occurs"""
        logging.error(f"Stream error: {error_msg}")
        self.status_bar.showMessage(f"Error: {error_msg}")

    def update_frame(self):
        """Update video frame display"""
        if not self.stream_receiver:
            return

        # Get frame from receiver
        frame = self.stream_receiver.get_frame(timeout=0.01)

        if frame is not None:
            self.current_frame = frame

            # Write to recorder if recording
            if self.recorder and self.recorder.is_recording:
                self.recorder.write_frame(frame)

            # Convert frame to QImage and display
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_BGR888)

            # Scale to fit label while maintaining aspect ratio
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(
                self.video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.video_label.setPixmap(scaled_pixmap)

            # Update FPS counter
            self.fps_counter += 1

    def update_statistics(self):
        """Update statistics display"""
        # Calculate FPS
        current_time = time.time()
        elapsed = current_time - self.fps_last_time
        if elapsed > 0:
            self.current_fps = self.fps_counter / elapsed
            self.fps_counter = 0
            self.fps_last_time = current_time

        # Build info string
        info_parts = []

        # Connection status
        status = "Connected" if self.is_connected else "Disconnected"
        info_parts.append(f"Status: {status}")

        # FPS
        if self.config.get('display', 'show_fps', True) and self.is_connected:
            info_parts.append(f"FPS: {self.current_fps:.1f}")

        # Recording status
        if self.recorder and self.recorder.is_recording:
            rec_status = self.recorder.get_status()
            duration = int(rec_status['duration'])
            info_parts.append(f"Recording: {duration}s ({rec_status['frame_count']} frames)")

        # Stream statistics
        if self.stream_receiver and self.is_connected:
            stats = self.stream_receiver.get_stats()

            # Queue size
            queue_size = stats['queue_size']
            info_parts.append(f"Queue: {queue_size}")

            # Calculate approximate latency based on queue size (at 30 FPS)
            latency_sec = queue_size / 30.0
            if latency_sec > 1.0:
                info_parts.append(f"Latency: ~{latency_sec:.1f}s")
            else:
                info_parts.append(f"Latency: ~{latency_sec*1000:.0f}ms")

            # Dropped frames
            if stats['frames_dropped'] > 0:
                info_parts.append(f"Dropped: {stats['frames_dropped']}")

        # Performance mode indicator
        perf_mode = self.config.get('advanced', 'performance_mode', 'balanced')
        mode_short = {'low_latency': 'LL', 'balanced': 'BAL', 'high_quality': 'HQ'}.get(perf_mode, perf_mode)
        info_parts.append(f"Mode: {mode_short}")

        # GPU acceleration status
        hw_accel = self.config.get('advanced', 'hw_accel', 'none')
        if hw_accel and hw_accel != 'none':
            info_parts.append(f"GPU: {hw_accel}")

        # Memory usage (if auto buffer sizing is enabled)
        if self.config.get('advanced', 'auto_buffer_sizing', False):
            try:
                import psutil
                mem = psutil.virtual_memory()
                info_parts.append(f"RAM: {mem.percent:.1f}%")
            except:
                pass  # psutil may not be installed

        self.info_label.setText(" | ".join(info_parts))

    def toggle_recording(self):
        """Toggle recording on/off"""
        if not self.recorder:
            return

        if self.recorder.is_recording:
            # Stop recording
            filename = self.recorder.stop_recording()
            self.record_button.setText("Start Recording")
            if filename:
                self.status_bar.showMessage(f"Recording saved: {filename}", 5000)
                QMessageBox.information(self, "Recording Saved", f"Video saved to:\n{filename}")
        else:
            # Start recording
            if self.current_frame is not None:
                height, width = self.current_frame.shape[:2]
                if self.recorder.start_recording(width, height):
                    self.record_button.setText("Stop Recording")
                    self.status_bar.showMessage("Recording started")
                else:
                    QMessageBox.critical(self, "Error", "Failed to start recording")
            else:
                QMessageBox.warning(self, "Warning", "No video frame available")

    def take_snapshot(self):
        """Take snapshot of current frame"""
        if self.current_frame is None:
            QMessageBox.warning(self, "Warning", "No video frame available")
            return

        if self.snapshot_manager:
            filename = self.snapshot_manager.capture_snapshot(self.current_frame)
            if filename:
                self.status_bar.showMessage(f"Snapshot saved: {filename}", 5000)
                logging.info(f"Snapshot saved to {filename}")
            else:
                QMessageBox.critical(self, "Error", "Failed to save snapshot")

    def closeEvent(self, event):
        """Handle window close event"""
        # Stop recording if active
        if self.recorder and self.recorder.is_recording:
            self.recorder.stop_recording()

        # Disconnect stream
        if self.is_connected:
            self.disconnect_stream()

        event.accept()


def run_app(config_path: str = "config.yaml"):
    """
    Run the video streaming application

    Args:
        config_path: Path to configuration file
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load configuration
    config = ConfigManager(config_path)

    # Create and run application
    app = QApplication(sys.argv)
    window = VideoStreamApp(config)
    window.show()

    sys.exit(app.exec_())
