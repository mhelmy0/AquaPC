#!/bin/bash
# RTP Video Streaming Client - Linux/macOS Launcher
#
# This script makes it easy to run the client on Linux/macOS

set -e

echo "===================================="
echo "RTP Video Streaming Client"
echo "===================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8+ from your package manager"
    exit 1
fi

echo "Python version:"
python3 --version
echo ""

# Check if dependencies are installed
if ! python3 -c "import cv2, PyQt5, yaml" &> /dev/null; then
    echo "Dependencies not found. Installing..."
    echo ""
    pip3 install -r requirements.txt
    echo ""
    echo "Dependencies installed successfully!"
    echo ""
fi

# Check if FFmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    echo "WARNING: FFmpeg not found"
    echo "Please install FFmpeg:"
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    echo "  macOS: brew install ffmpeg"
    echo ""
    read -p "Press Enter to continue anyway or Ctrl+C to exit..."
fi

# Run the application
echo "Starting application..."
echo ""
python3 main.py

# Exit with the same code as the Python script
exit $?
