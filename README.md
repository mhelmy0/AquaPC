# RTP Video Streaming Client

A lightweight, scalable Python application for receiving and displaying live H.264 video streams from a Raspberry Pi server over RTP. This client provides real-time video display, on-demand recording, and snapshot capture capabilities with a simple, intuitive GUI.

## Features

- **Live Stream Display**: Receive and display RTP H.264 video in real-time with minimal latency
- **Recording**: Start/stop recording to video file (MP4, MKV, AVI) on demand
- **Snapshot Capture**: Take snapshots from the live stream at any time
- **Auto Buffer Sizing**: Automatically allocates up to 70% of free RAM for optimal buffering
- **Network Resilience**: Handles packet loss and network errors gracefully
- **Auto-Reconnect**: Automatic reconnection with health monitoring
- **Simple GUI**: Clean interface with PyQt5 showing:
  - Live video feed
  - Connection status
  - Recording controls and status
  - FPS counter and statistics
  - Real-time RAM usage monitoring
- **Cross-platform**: Works on Windows, Linux, and macOS
- **Configurable**: Easy YAML configuration for all settings
- **Scalable Architecture**: Clean, modular design for easy extension

## Requirements

### Software Dependencies

- **Python 3.8+**
- **FFmpeg**: For receiving and decoding RTP stream
  - Download from: https://ffmpeg.org/download.html
  - Must be in system PATH or specified in config
- **Python packages** (see requirements.txt):
  - opencv-python >= 4.8.0
  - PyQt5 >= 5.15.0
  - PyYAML >= 6.0
  - numpy >= 1.24.0
  - psutil >= 5.9.0 (for auto buffer sizing)

### Server Configuration

This client is designed to work with a Raspberry Pi streaming H.264 video over RTP:

- **Protocol**: RTP over UDP
- **Codec**: H.264 (hardware encoded)
- **Default Port**: 5000
- **Server IP**: 192.168.100.41 (configurable)

Example FFmpeg command on server:
```bash
ffmpeg -re -f h264 -i - -c:v copy -an -f rtp -rtpflags latm -pkt_size 1200 -sdp_file /tmp/stream.sdp rtp://192.168.100.41:5000
```

## Installation

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install opencv-python PyQt5 PyYAML numpy
```

### Step 2: Install FFmpeg

#### Windows:
1. Download FFmpeg from https://ffmpeg.org/download.html
2. Extract to a folder (e.g., `C:\ffmpeg`)
3. Add `C:\ffmpeg\bin` to system PATH
4. Verify: `ffmpeg -version`

#### Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install ffmpeg
```

#### macOS:
```bash
brew install ffmpeg
```

### Step 3: Configure Application

Edit `config.yaml` to match your setup:

```yaml
stream:
  source_ip: "192.168.100.41"  # Your Raspberry Pi IP
  rtp_port: 5000               # RTP port
```

See [Configuration](#configuration) section for detailed options.

## Usage

### Basic Usage

Run the application with default configuration:

```bash
python main.py
```

### With Custom Configuration

```bash
python main.py --config my_config.yaml
```

### Command Line Options

```bash
python main.py --help
```

Options:
- `--config CONFIG_PATH`: Path to configuration file (default: config.yaml)
- `--log-level LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)

### Application Controls

1. **Connect**: Click "Connect" to start receiving the stream
2. **Record**: Click "Start Recording" to begin recording (available when connected)
3. **Snapshot**: Click "Take Snapshot" to capture current frame
4. **Disconnect**: Click "Disconnect" to stop the stream

### Keyboard Shortcuts

- Press `Ctrl+C` in terminal to exit

## Configuration

The `config.yaml` file contains all application settings:

### Stream Settings

```yaml
stream:
  source_ip: "192.168.100.41"  # Raspberry Pi IP address
  rtp_port: 5000               # RTP streaming port
  protocol: "rtp"              # Protocol (rtp/udp)
  codec: "h264"                # Video codec
  sdp_file: null               # Optional: path to SDP file
```

### Display Settings

```yaml
display:
  window_title: "AquaCam Live Stream"
  width: 1280                  # Display resolution
  height: 720
  show_fps: true               # Show FPS counter
  show_bitrate: false          # Show bitrate
  fullscreen: false            # Start in fullscreen
```

### Recording Settings

```yaml
recording:
  output_dir: "./recordings"   # Output directory
  format: "mp4"                # Format: mp4, mkv, avi
  codec: "h264"                # Codec for recording
  filename_pattern: "recording_%Y%m%d_%H%M%S"  # Filename with timestamp
  fps: 30                      # Recording frame rate
```

### Snapshot Settings

```yaml
snapshot:
  output_dir: "./snapshots"    # Output directory
  format: "jpg"                # Format: jpg, png
  quality: 95                  # JPEG quality (0-100)
  filename_pattern: "snapshot_%Y%m%d_%H%M%S"
```

### Advanced Settings

```yaml
advanced:
  buffer_size: 1024            # Frame buffer size
  reconnect_interval: 5        # Reconnection delay (seconds)
  max_reconnect_attempts: 0    # 0 = infinite
  ffmpeg_path: "ffmpeg"        # Path to FFmpeg executable
  frame_drop_threshold: 10     # Drop frames if queue exceeds this
  log_level: "INFO"            # Logging level
```

## Testing

### Test Stream Connectivity

Before running the client, verify the stream is accessible:

```bash
ffplay -protocol_whitelist file,rtp,udp rtp://192.168.100.41:5000
```

If this works, the client should connect successfully.

### Test with VLC

You can also test with VLC Media Player:
1. Open VLC
2. Media → Open Network Stream
3. Enter: `rtp://192.168.100.41:5000`
4. Click Play

### Check Network Connectivity

```bash
# Ping the Raspberry Pi
ping 192.168.100.41

# Check if port 5000 is open (Linux/Mac)
nc -zv 192.168.100.41 5000

# Windows equivalent
Test-NetConnection -ComputerName 192.168.100.41 -Port 5000
```

## Troubleshooting

### Issue: "Connection failed" or "No stream"

**Solutions:**
1. Verify Raspberry Pi is streaming:
   - Check server is running
   - Verify IP address (192.168.100.41)
   - Confirm port 5000 is used
2. Check network connectivity (ping Raspberry Pi)
3. Verify firewall isn't blocking UDP port 5000
4. Test with `ffplay` (see Testing section)

### Issue: "FFmpeg not found"

**Solutions:**
1. Install FFmpeg (see Installation section)
2. Verify FFmpeg is in PATH: `ffmpeg -version`
3. Specify full path in config.yaml:
   ```yaml
   advanced:
     ffmpeg_path: "C:/ffmpeg/bin/ffmpeg.exe"  # Windows
     # or
     ffmpeg_path: "/usr/bin/ffmpeg"           # Linux/Mac
   ```

### Issue: Poor video quality or lag

**Solutions:**
1. Reduce resolution on server (1280x720 instead of 1920x1080)
2. Lower bitrate on server
3. Increase `frame_drop_threshold` in config.yaml
4. Check network bandwidth
5. Use wired connection instead of WiFi

### Issue: Recording fails

**Solutions:**
1. Check output directory exists and is writable
2. Verify codec is supported (try 'h264' or 'mp4v')
3. Ensure enough disk space
4. Check logs for detailed error messages

### Issue: Application crashes

**Solutions:**
1. Check logs in `client.log`
2. Run with debug logging:
   ```bash
   python main.py --log-level DEBUG
   ```
3. Verify all dependencies are installed
4. Update dependencies to latest versions

### Issue: Black screen but connected

**Solutions:**
1. Verify server is actively streaming
2. Check stream format matches configuration
3. Try different display resolution in config
4. Restart both client and server

## Project Structure

```
client_v3/
├── main.py                  # Entry point
├── config.yaml              # Configuration file
├── requirements.txt         # Python dependencies
├── README.md               # This file
├── client.log              # Application logs
├── src/                    # Source code
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── stream_receiver.py  # RTP stream reception
│   ├── recorder.py         # Video recording
│   ├── snapshot.py         # Snapshot capture
│   └── video_display.py    # GUI application
├── recordings/             # Recorded videos (created automatically)
└── snapshots/              # Saved snapshots (created automatically)
```

## Architecture

The application follows a modular architecture:

```
┌─────────────────────────────────────────┐
│          Video Display GUI              │
│            (PyQt5)                      │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┼──────────┬──────────┐
    │          │          │          │
┌───▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐
│Stream │ │Recorder│ │Snapshot│ │ Config │
│Receiver│ │        │ │Manager │ │Manager │
└───┬───┘ └───┬────┘ └────────┘ └────────┘
    │         │
┌───▼─────────▼───┐
│  FFmpeg Process  │
│  (RTP → H.264)   │
└──────────────────┘
```

### Key Components

1. **ConfigManager**: Loads and manages YAML configuration
2. **StreamReceiver**: Receives RTP stream via FFmpeg subprocess
3. **Recorder**: Records frames to video file using OpenCV
4. **SnapshotManager**: Captures and saves individual frames
5. **VideoStreamApp**: Main GUI application (PyQt5)

## Extending the Application

The modular design makes it easy to add features:

### Add New Video Filters

```python
# In video_display.py, modify update_frame()
def update_frame(self):
    frame = self.stream_receiver.get_frame()

    # Add your custom filter here
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # Example: grayscale

    # ... rest of the code
```

### Add Multi-Stream Support

Create multiple `StreamReceiver` instances with different configurations.

### Add Audio Support

Modify FFmpeg command to include audio streams and use PyAudio for playback.

## Documentation

Complete documentation is available in the [docs/](docs/) directory:

### Quick Start
- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - 5-minute setup guide

### Configuration & Optimization
- **[docs/LOW_LATENCY_GUIDE.md](docs/LOW_LATENCY_GUIDE.md)** - Complete low latency optimization guide
- **[docs/ULTRA_LOW_LATENCY_CONFIG.md](docs/ULTRA_LOW_LATENCY_CONFIG.md)** - Current 400ms configuration
- **[docs/MEMORY_OPTIMIZATION.md](docs/MEMORY_OPTIMIZATION.md)** - Memory buffer optimization

### Troubleshooting
- **[docs/TROUBLESHOOTING_QUICK_REFERENCE.md](docs/TROUBLESHOOTING_QUICK_REFERENCE.md)** - Quick troubleshooting guide
- **[docs/WINDOWS_COMMANDS.md](docs/WINDOWS_COMMANDS.md)** - Windows PowerShell commands
- **[docs/QUICK_FIX_SUMMARY.md](docs/QUICK_FIX_SUMMARY.md)** - Summary of fixes

### Technical
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Technical architecture
- **[docs/CHANGELOG.md](docs/CHANGELOG.md)** - Version history
- **[docs/README.md](docs/README.md)** - Full documentation index

## Performance Tips

**For detailed optimization, see [docs/LOW_LATENCY_GUIDE.md](docs/LOW_LATENCY_GUIDE.md)**

Quick tips:
1. **Ultra-Low Latency**: See [docs/ULTRA_LOW_LATENCY_CONFIG.md](docs/ULTRA_LOW_LATENCY_CONFIG.md)
2. **GPU Acceleration**: Set `hw_accel: "auto"` in config (enabled by default)
3. **Network**: Use wired Ethernet for best performance
4. **Memory**: Adjust `performance_mode` in config (low_latency/balanced/high_quality)

## License

This project is provided as-is for educational and personal use.

## Contributing

This is a standalone project, but improvements are welcome:
- Add new features
- Fix bugs
- Improve documentation
- Add tests

## Changelog

### Version 1.0.0 (2025-01-17)
- Initial release
- Basic RTP streaming support
- Recording and snapshot features
- PyQt5 GUI
- YAML configuration

## Support

For issues and questions:
1. Check the Troubleshooting section
2. Review the logs in `client.log`
3. Run with `--log-level DEBUG` for detailed output

## Acknowledgments

- Built with OpenCV, PyQt5, and FFmpeg
- Designed for Raspberry Pi camera streaming
- Inspired by minimal, efficient video streaming solutions
