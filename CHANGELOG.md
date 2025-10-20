# Changelog

All notable changes to the RTP Video Streaming Client project will be documented in this file.

## [1.0.0] - 2025-01-17

### Added

#### Core Features
- **Live RTP Stream Reception**: Receive and display H.264 video over RTP/UDP
- **Video Recording**: On-demand recording to MP4/MKV/AVI formats
- **Snapshot Capture**: Single frame capture to JPEG/PNG
- **PyQt5 GUI**: Clean, intuitive interface with real-time statistics
- **Cross-Platform**: Full support for Windows, Linux, and macOS

#### SDP Configuration Support
- **SDP Content in Config**: Embedded SDP configuration in [config.yaml](config.yaml:11-22)
- **Automatic SDP File Creation**: Temporary SDP file generation from config
- **Flexible Input**: Support for SDP file path, SDP content, or direct RTP URL
- **Priority System**: SDP file > SDP content > direct RTP URL

#### Comprehensive Logging System
- **Multi-File Logging**: Separate logs for different purposes
  - `logs/app.log` - All application logs
  - `logs/errors.log` - Error messages only
  - `logs/warnings.log` - Warning messages only
  - `logs/events.log` - Application events (connect, record, snapshot)
- **Rotating Log Files**: Automatic log rotation (10 MB per file, 5 backups)
- **Event Tracking**: Dedicated event logging for monitoring
- **Component Tagging**: Each log entry tagged with source component
- **Structured Logging**: Consistent format with timestamps

#### Components

**ConfigManager** ([src/config.py](src/config.py:1))
- YAML configuration loading and validation
- SDP content parsing and temporary file creation
- FFmpeg command generation with SDP support
- Automatic directory creation

**StreamReceiver** ([src/stream_receiver.py](src/stream_receiver.py:1))
- FFmpeg subprocess management
- Threaded frame reception
- Frame buffering with drop control
- Statistics tracking

**Recorder** ([src/recorder.py](src/recorder.py:1))
- OpenCV VideoWriter integration
- Multiple codec support (H.264, XVID, etc.)
- Automatic timestamped filenames
- Recording statistics

**SnapshotManager** ([src/snapshot.py](src/snapshot.py:1))
- Frame capture to image file
- JPEG/PNG format support
- Quality settings
- Timestamped filenames

**AppLogger** ([src/logger.py](src/logger.py:1))
- Centralized logging system
- Multiple log files (app, errors, warnings, events)
- Rotating file handlers
- Event tracking methods
- Component-based logging

**VideoStreamApp** ([src/video_display.py](src/video_display.py:1))
- PyQt5 GUI application
- Real-time video display
- Control buttons (Connect, Record, Snapshot)
- Statistics display (FPS, queue size, recording status)
- Connection status indicator

#### Configuration

**config.yaml** ([config.yaml](config.yaml:1))
- Stream settings (IP, port, codec)
- SDP configuration (embedded content)
- Display settings (resolution, FPS counter)
- Recording settings (format, codec, output)
- Snapshot settings (format, quality)
- Advanced settings (buffer, reconnection, logging)

#### Documentation

**README.md** ([README.md](README.md:1))
- Complete user guide (450+ lines)
- Installation instructions
- Usage guide
- Configuration reference
- Troubleshooting section
- Performance tips

**QUICKSTART.md** ([QUICKSTART.md](QUICKSTART.md:1))
- 5-minute setup guide
- Prerequisites checklist
- Quick test procedures
- Common issues

**ARCHITECTURE.md** ([ARCHITECTURE.md](ARCHITECTURE.md:1))
- Technical architecture documentation (450+ lines)
- Component descriptions
- Data flow diagrams
- Threading model
- Extension points

**PROJECT_SUMMARY.md** ([PROJECT_SUMMARY.md](PROJECT_SUMMARY.md:1))
- Project overview
- Feature list
- File structure
- Success criteria

#### Support Files

**Launchers**
- [run.bat](run.bat:1) - Windows launcher with dependency checking
- [run.sh](run.sh:1) - Linux/macOS launcher script

**Utilities**
- [verify_installation.py](verify_installation.py:1) - Installation verification script
- [requirements.txt](requirements.txt:1) - Python dependencies

**Git**
- [.gitignore](.gitignore:1) - Git ignore rules (including logs/)

### Technical Details

#### Logging Architecture

```
Application
    │
    ├─→ logs/app.log        (All logs)
    ├─→ logs/errors.log     (Errors only)
    ├─→ logs/warnings.log   (Warnings only)
    └─→ logs/events.log     (Events only)
```

**Log Events**:
- `STARTUP` - Application started
- `SHUTDOWN` - Application stopped
- `CONNECTION` - Stream connection status change
- `STREAM` - Stream events (connect, disconnect, frame received)
- `RECORDING` - Recording events (start, stop, frame written)
- `SNAPSHOT` - Snapshot captured
- `ERROR` - Error occurred

#### SDP Configuration

**Three Ways to Configure Stream Input**:

1. **Direct RTP URL** (default):
```yaml
stream:
  source_ip: "192.168.100.41"
  rtp_port: 5000
  sdp_file: null
  sdp_content: ""
```

2. **SDP File Path**:
```yaml
stream:
  sdp_file: "/path/to/stream.sdp"
```

3. **Embedded SDP Content** (new):
```yaml
stream:
  sdp_content: |
    v=0
    o=- 0 0 IN IP4 127.0.0.1
    s=Raspberry Pi Camera Stream
    c=IN IP4 0.0.0.0
    t=0 0
    m=video 5000 RTP/AVP 96
    a=rtpmap:96 H264/90000
    a=fmtp:96 packetization-mode=1
```

#### Command Line Options

**New Options**:
- `--log-dir DIR` - Specify log directory (default: logs)
- `--log-level LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR)

**Example**:
```bash
python main.py --config config.yaml --log-dir ./logs --log-level DEBUG
```

### Dependencies

**Python Packages**:
- opencv-python >= 4.8.0
- PyQt5 >= 5.15.0
- PyYAML >= 6.0
- numpy >= 1.24.0

**External**:
- FFmpeg (any recent version)

### File Statistics

- **Source Code**: ~1,300 lines of Python
- **Documentation**: ~1,100 lines of Markdown
- **Configuration**: ~55 lines of YAML
- **Total Files**: 19 files committed

### Git Repository

**Initial Commit**: `068e8b0`
- 19 files changed
- 3,325 insertions
- Complete working application

### Known Limitations

1. Single stream at a time
2. Video only (no audio)
3. H.264 codec only (tested)
4. Local network designed
5. No authentication

### Future Enhancements

Planned features for future versions:
- Multi-stream support
- Audio playback
- Motion detection
- Hardware acceleration
- Authentication system
- H.265 codec support

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2025-01-17 | Initial release with full features |

---

**Note**: This project follows [Semantic Versioning](https://semver.org/).
