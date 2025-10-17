#!/usr/bin/env python3
"""
Installation Verification Script
Checks if all dependencies and requirements are met
"""

import sys
import subprocess
import os


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_status(check, status, message=""):
    """Print a status line with colored output"""
    status_symbol = "✓" if status else "✗"
    status_text = "OK" if status else "FAIL"
    print(f"[{status_symbol}] {check:.<40} {status_text}")
    if message:
        print(f"    {message}")
    return status


def check_python_version():
    """Check if Python version is 3.8+"""
    version = sys.version_info
    is_ok = version.major == 3 and version.minor >= 8
    return print_status(
        "Python version (3.8+)",
        is_ok,
        f"Current: {version.major}.{version.minor}.{version.micro}"
    )


def check_module(module_name, import_name=None):
    """Check if a Python module is installed"""
    if import_name is None:
        import_name = module_name

    try:
        __import__(import_name)
        return print_status(f"Module: {module_name}", True)
    except ImportError as e:
        return print_status(f"Module: {module_name}", False, f"Error: {e}")


def check_ffmpeg():
    """Check if FFmpeg is installed"""
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        is_ok = result.returncode == 0
        if is_ok:
            version_line = result.stdout.decode().split('\n')[0]
            return print_status("FFmpeg", True, version_line)
        else:
            return print_status("FFmpeg", False)
    except FileNotFoundError:
        return print_status("FFmpeg", False, "Not found in PATH")
    except Exception as e:
        return print_status("FFmpeg", False, f"Error: {e}")


def check_file_exists(filepath, description):
    """Check if a file exists"""
    exists = os.path.exists(filepath)
    return print_status(description, exists, f"Path: {filepath}")


def check_directory_writable(dirpath, description):
    """Check if a directory exists and is writable"""
    if not os.path.exists(dirpath):
        return print_status(description, False, f"Directory does not exist: {dirpath}")

    is_writable = os.access(dirpath, os.W_OK)
    return print_status(description, is_writable, f"Path: {dirpath}")


def main():
    """Run all verification checks"""
    print_header("RTP Video Streaming Client - Installation Verification")

    print("This script will verify that all dependencies are installed correctly.\n")

    all_ok = True

    # Python version
    print_header("Python Environment")
    all_ok &= check_python_version()

    # Python modules
    print_header("Python Dependencies")
    all_ok &= check_module("opencv-python", "cv2")
    all_ok &= check_module("PyQt5", "PyQt5.QtWidgets")
    all_ok &= check_module("PyYAML", "yaml")
    all_ok &= check_module("numpy", "numpy")

    # FFmpeg
    print_header("External Dependencies")
    all_ok &= check_ffmpeg()

    # Project files
    print_header("Project Files")
    all_ok &= check_file_exists("config.yaml", "Configuration file")
    all_ok &= check_file_exists("main.py", "Main entry point")
    all_ok &= check_file_exists("requirements.txt", "Requirements file")
    all_ok &= check_file_exists("src/config.py", "Config module")
    all_ok &= check_file_exists("src/stream_receiver.py", "StreamReceiver module")
    all_ok &= check_file_exists("src/recorder.py", "Recorder module")
    all_ok &= check_file_exists("src/snapshot.py", "Snapshot module")
    all_ok &= check_file_exists("src/video_display.py", "VideoDisplay module")

    # Output directories
    print_header("Output Directories")
    all_ok &= check_directory_writable("recordings", "Recordings directory")
    all_ok &= check_directory_writable("snapshots", "Snapshots directory")

    # Final result
    print_header("Verification Result")
    if all_ok:
        print("✓ All checks passed! You're ready to run the application.")
        print("\nRun the application with:")
        print("  python main.py")
        return 0
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Install FFmpeg: https://ffmpeg.org/download.html")
        print("  - Check file permissions")
        return 1


if __name__ == "__main__":
    sys.exit(main())
