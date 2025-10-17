#!/usr/bin/env python3
"""
RTP Video Streaming Client - Main Entry Point

A lightweight application for receiving and displaying live H.264 video
from a Raspberry Pi server over RTP.

Features:
- Live stream display with minimal latency
- On-demand recording to video file
- Snapshot capture
- Simple, intuitive GUI

Usage:
    python main.py [--config CONFIG_PATH]

Arguments:
    --config    Path to configuration file (default: config.yaml)

Example:
    python main.py --config config.yaml
"""

import sys
import os
import argparse

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.video_display import run_app
from src.logger import setup_logger


def main():
    """Main entry point"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='RTP Video Streaming Client',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    parser.add_argument(
        '--log-dir',
        type=str,
        default='logs',
        help='Log directory (default: logs)'
    )

    args = parser.parse_args()

    # Setup application logger
    logger = setup_logger(log_dir=args.log_dir, log_level=args.log_level)

    # Check if config file exists
    if not os.path.exists(args.config):
        logger.error(f"Configuration file not found: {args.config}", "Main")
        print(f"Error: Configuration file '{args.config}' not found!")
        print("Please create a config.yaml file or specify a valid config path.")
        sys.exit(1)

    # Run application
    try:
        logger.info("Starting RTP Video Streaming Client", "Main")
        logger.event("STARTUP", "Application started")
        run_app(args.config)
    except KeyboardInterrupt:
        logger.info("Application interrupted by user", "Main")
        logger.event("SHUTDOWN", "Application stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", "Main", exc_info=True)
        logger.event("ERROR", f"Fatal error: {e}", "Main")
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
