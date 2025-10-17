@echo off
REM RTP Video Streaming Client - Windows Launcher
REM
REM This batch file makes it easy to run the client on Windows

echo ====================================
echo RTP Video Streaming Client
echo ====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

REM Check if dependencies are installed
python -c "import cv2, PyQt5, yaml" >nul 2>&1
if errorlevel 1 (
    echo Dependencies not found. Installing...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
    echo.
    echo Dependencies installed successfully!
    echo.
)

REM Check if FFmpeg is available
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo WARNING: FFmpeg not found in PATH
    echo Please install FFmpeg from https://ffmpeg.org/download.html
    echo.
    pause
)

REM Run the application
echo Starting application...
echo.
python main.py

REM Pause if there was an error
if errorlevel 1 (
    echo.
    echo Application exited with an error
    pause
)
