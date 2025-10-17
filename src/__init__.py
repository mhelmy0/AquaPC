"""
RTP Video Streaming Client
A lightweight client for receiving and displaying H.264 video from Raspberry Pi
"""

__version__ = "1.0.0"
__author__ = "RTP Streaming Client"

from .config import ConfigManager
from .stream_receiver import StreamReceiver
from .recorder import Recorder
from .snapshot import SnapshotManager
from .video_display import VideoStreamApp, run_app
from .logger import AppLogger, get_logger, setup_logger

__all__ = [
    'ConfigManager',
    'StreamReceiver',
    'Recorder',
    'SnapshotManager',
    'VideoStreamApp',
    'run_app',
    'AppLogger',
    'get_logger',
    'setup_logger'
]
