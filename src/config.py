"""
Configuration Manager for RTP Video Streaming Client
Handles loading and accessing configuration from YAML file
"""

import yaml
import os
import logging
from typing import Any, Dict


class ConfigManager:
    """Manages application configuration from YAML file"""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration manager

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
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

        cmd = [
            ffmpeg_path,
            '-protocol_whitelist', 'file,rtp,udp',
            '-i', input_source,
        ]

        if output_format == "rawvideo":
            cmd.extend([
                '-f', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-'  # Output to stdout
            ])

        return cmd

    def __repr__(self) -> str:
        """String representation of configuration"""
        return f"ConfigManager(config_path='{self.config_path}')"
