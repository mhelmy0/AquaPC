"""
Configuration Manager for RTP Video Streaming Client
Handles loading and accessing configuration from YAML file
"""

import yaml
import os
import logging
from typing import Any, Dict, Optional


class ConfigManager:
    """Manages application configuration from YAML file"""

    def __init__(self, config_path: str = "config.yaml", logger=None):
        """
        Initialize configuration manager

        Args:
            config_path: Path to YAML configuration file
            logger: Optional logger instance
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.logger = logger
        self.optimal_buffers: Optional[Dict[str, int]] = None
        self.load_config()

    def load_config(self) -> None:
        """Load configuration from YAML file"""
        try:
            if not os.path.exists(self.config_path):
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)

            # Validate required sections
            required_sections = ['stream', 'display', 'recording', 'snapshot', 'advanced']
            for section in required_sections:
                if section not in self.config:
                    raise ValueError(f"Missing required configuration section: {section}")

            # Create output directories if they don't exist
            self._create_directories()

            # Calculate optimal buffers if auto_buffer_sizing is enabled
            if self.get('advanced', 'auto_buffer_sizing', False):
                self._calculate_optimal_buffers()

            logging.info(f"Configuration loaded successfully from {self.config_path}")

        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            raise

    def _create_directories(self) -> None:
        """Create output directories if they don't exist"""
        recording_dir = self.get('recording', 'output_dir')
        snapshot_dir = self.get('snapshot', 'output_dir')

        for directory in [recording_dir, snapshot_dir]:
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logging.info(f"Created directory: {directory}")

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get configuration value

        Args:
            section: Configuration section name
            key: Configuration key name
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        try:
            return self.config.get(section, {}).get(key, default)
        except Exception:
            return default

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section

        Args:
            section: Configuration section name

        Returns:
            Dictionary containing section configuration
        """
        return self.config.get(section, {})

    def get_stream_url(self) -> str:
        """
        Build RTP stream URL from configuration

        Returns:
            RTP stream URL string
        """
        source_ip = self.get('stream', 'source_ip')
        rtp_port = self.get('stream', 'rtp_port')
        protocol = self.get('stream', 'protocol', 'rtp')

        return f"{protocol}://{source_ip}:{rtp_port}"

    def get_sdp_content(self) -> str:
        """
        Get SDP content from configuration

        Returns:
            SDP content string or empty string if not configured
        """
        sdp_content = self.get('stream', 'sdp_content', '')
        if sdp_content:
            return sdp_content.strip()
        return ''

    def create_temp_sdp_file(self) -> str:
        """
        Create temporary SDP file from configuration content

        Returns:
            Path to temporary SDP file or empty string if no SDP content
        """
        import tempfile

        sdp_content = self.get_sdp_content()
        if not sdp_content:
            return ''

        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.sdp', delete=False)
        temp_file.write(sdp_content)
        temp_file.close()

        logging.info(f"Created temporary SDP file: {temp_file.name}")
        return temp_file.name

    def get_ffmpeg_command(self, output_format: str = "rawvideo") -> list:
        """
        Build FFmpeg command for stream reception

        Args:
            output_format: Output format (rawvideo, h264, etc.)

        Returns:
            List of command arguments for FFmpeg
        """
        ffmpeg_path = self.get('advanced', 'ffmpeg_path', 'ffmpeg')
        stream_url = self.get_stream_url()
        sdp_file = self.get('stream', 'sdp_file')

        # Priority: explicit SDP file > SDP content > direct RTP URL
        input_source = stream_url
        if sdp_file:
            input_source = sdp_file
        elif self.get_sdp_content():
            # Create temporary SDP file from content
            temp_sdp = self.create_temp_sdp_file()
            if temp_sdp:
                input_source = temp_sdp

        # Build FFmpeg command with error resilience options
        cmd = [
            ffmpeg_path,
            '-protocol_whitelist', 'file,rtp,udp',
        ]

        # Add error resilience flags
        ignore_errors = self.get('advanced', 'ignore_decode_errors', True)
        if ignore_errors:
            cmd.extend([
                '-fflags', '+genpts+igndts',     # Generate PTS, ignore DTS errors
                '-err_detect', 'ignore_err',      # Ignore decoding errors
            ])

        # Add UDP buffer size (auto-calculated or from config)
        udp_buffer = self.get_udp_buffer_size()
        if udp_buffer:
            cmd.extend(['-buffer_size', str(udp_buffer)])

        # Add input source
        cmd.extend(['-i', input_source])

        if output_format == "rawvideo":
            cmd.extend([
                '-f', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-vf', 'setpts=PTS-STARTPTS',   # Reset timestamps
                '-'  # Output to stdout
            ])

        return cmd

    def _calculate_optimal_buffers(self) -> None:
        """Calculate optimal buffer sizes based on available RAM"""
        try:
            from src.memory_manager import get_optimal_buffers

            frame_width = self.get('display', 'width', 1920)
            frame_height = self.get('display', 'height', 1080)
            max_ram_percent = self.get('advanced', 'max_ram_usage_percent', 70)

            self.optimal_buffers = get_optimal_buffers(
                frame_width=frame_width,
                frame_height=frame_height,
                max_ram_percent=max_ram_percent,
                logger=self.logger
            )

            if self.logger:
                self.logger.info(f"Auto buffer sizing enabled: Using {self.optimal_buffers['total_memory_mb']:.1f} MB", "ConfigManager")
            else:
                logging.info(f"ConfigManager: Auto buffer sizing enabled: Using {self.optimal_buffers['total_memory_mb']:.1f} MB")

        except Exception as e:
            error_msg = f"Failed to calculate optimal buffers: {e}. Using default values."
            if self.logger:
                self.logger.warning(error_msg, "ConfigManager")
            else:
                logging.warning(f"ConfigManager: {error_msg}")
            self.optimal_buffers = None

    def get_buffer_size(self) -> int:
        """
        Get frame buffer size (auto-calculated or from config)

        Returns:
            Frame buffer size
        """
        if self.optimal_buffers:
            return self.optimal_buffers['frame_buffer_size']
        return self.get('advanced', 'buffer_size', 1024)

    def get_recording_queue_size(self) -> int:
        """
        Get recording queue size (auto-calculated or from config)

        Returns:
            Recording queue size
        """
        if self.optimal_buffers:
            return self.optimal_buffers['recording_queue_size']
        return self.get('advanced', 'recording_queue_size', 100)

    def get_udp_buffer_size(self) -> int:
        """
        Get UDP buffer size (auto-calculated or from config)

        Returns:
            UDP buffer size in bytes
        """
        if self.optimal_buffers:
            return self.optimal_buffers['udp_buffer_size']
        return self.get('advanced', 'udp_buffer_size', 65536)

    def __repr__(self) -> str:
        """String representation of configuration"""
        return f"ConfigManager(config_path='{self.config_path}')"
