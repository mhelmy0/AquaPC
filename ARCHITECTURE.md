# Architecture Documentation

## Overview

The RTP Video Streaming Client is designed with a modular, scalable architecture that separates concerns and makes it easy to extend or modify functionality.

## Design Principles

1. **Separation of Concerns**: Each component has a single, well-defined responsibility
2. **Modularity**: Components are loosely coupled and can be used independently
3. **Extensibility**: Easy to add new features without modifying core components
4. **Simplicity**: Minimal dependencies, clear code structure
5. **Configurability**: All settings externalized to YAML configuration

## Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Main Application                     │
│                      (main.py)                          │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              VideoStreamApp (GUI Layer)                 │
│                   (video_display.py)                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │  - PyQt5 Window & UI Controls                   │   │
│  │  - Frame Display (QLabel + QPixmap)             │   │
│  │  - Timer Management                             │   │
│  │  - Event Handling                               │   │
│  └─────────────────────────────────────────────────┘   │
└───┬──────────────┬──────────────┬──────────────┬────────┘
    │              │              │              │
    ▼              ▼              ▼              ▼
┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Stream  │  │ Recorder │  │ Snapshot │  │  Config  │
│Receiver │  │          │  │ Manager  │  │ Manager  │
│         │  │          │  │          │  │          │
└────┬────┘  └────┬─────┘  └──────────┘  └──────────┘
     │            │
     │            │
     ▼            ▼
┌─────────────────────────┐
│   FFmpeg Subprocess     │
│   (RTP → Raw Frames)    │
└─────────────────────────┘
     │
     ▼
┌─────────────────────────┐
│  Network (RTP/UDP)      │
│  Raspberry Pi Server    │
└─────────────────────────┘
```

## Core Components

### 1. ConfigManager (config.py)

**Responsibility**: Load and manage application configuration

**Key Features**:
- YAML configuration parsing
- Configuration validation
- Default value handling
- Directory creation
- FFmpeg command generation

**API**:
```python
config = ConfigManager('config.yaml')
value = config.get('section', 'key', default)
section = config.get_section('section_name')
url = config.get_stream_url()
cmd = config.get_ffmpeg_command()
```

**Design Notes**:
- Singleton-like usage (one config per application)
- Fails fast on missing configuration
- Creates output directories automatically

### 2. StreamReceiver (stream_receiver.py)

**Responsibility**: Receive and decode RTP stream using FFmpeg

**Key Features**:
- FFmpeg subprocess management
- Frame buffering with queue
- Frame dropping for latency control
- Statistics tracking
- Callback support for events

**API**:
```python
receiver = StreamReceiver(ffmpeg_cmd, width, height)
receiver.on_connect = callback_fn
receiver.start()
frame = receiver.get_frame(timeout=0.1)
stats = receiver.get_stats()
receiver.stop()
```

**Threading Model**:
- Main thread: FFmpeg process management
- Worker thread: Frame reception loop
- Thread-safe queue for frame passing

**Design Notes**:
- Non-blocking frame retrieval
- Automatic frame dropping to prevent lag
- Graceful shutdown on errors

### 3. Recorder (recorder.py)

**Responsibility**: Record video frames to file

**Key Features**:
- OpenCV VideoWriter integration
- Multiple codec support
- Automatic filename generation
- Recording statistics

**API**:
```python
recorder = Recorder(output_dir, filename_pattern, format, codec, fps)
recorder.start_recording(width, height)
recorder.write_frame(frame)
filename = recorder.stop_recording()
status = recorder.get_status()
```

**Design Notes**:
- Synchronous frame writing (no buffering)
- Timestamped filenames
- Codec auto-detection

### 4. SnapshotManager (snapshot.py)

**Responsibility**: Capture and save single frames

**Key Features**:
- Multiple image format support
- Quality/compression settings
- Automatic filename generation
- Statistics tracking

**API**:
```python
manager = SnapshotManager(output_dir, filename_pattern, format, quality)
filename = manager.capture_snapshot(frame)
stats = manager.get_stats()
```

**Design Notes**:
- Stateless operation (no buffering)
- Format-specific encoding parameters
- Error resilience

### 5. VideoStreamApp (video_display.py)

**Responsibility**: Main GUI application and coordination

**Key Features**:
- PyQt5 window management
- User interaction handling
- Component coordination
- Real-time statistics display
- Timer-based frame updates

**Event Flow**:
```
User Action → Button Click → Event Handler → Component Method → Update UI
```

**Timer Architecture**:
- Frame Timer (33ms): Update video display
- Stats Timer (1000ms): Update statistics

**Design Notes**:
- Single-threaded UI (PyQt5 requirement)
- Frame display in main thread
- Callbacks from StreamReceiver run in worker thread

## Data Flow

### Frame Reception Flow

```
[Raspberry Pi] → RTP/UDP → [FFmpeg Subprocess] → stdout (raw bytes)
                                ↓
                    [StreamReceiver Thread]
                                ↓
                      Raw bytes → NumPy array
                                ↓
                        [Frame Queue]
                                ↓
                    [GUI Main Thread Timer]
                                ↓
            Queue.get() → frame → Display/Record
```

### Recording Flow

```
[Frame Queue] → get_frame() → [Current Frame]
                                    ↓
                        [Recorder.write_frame()]
                                    ↓
                          [OpenCV VideoWriter]
                                    ↓
                              [Output File]
```

### Snapshot Flow

```
[Current Frame] → User Click → [SnapshotManager.capture_snapshot()]
                                            ↓
                                  cv2.imwrite() → [Image File]
```

## Threading Model

### Threads

1. **Main Thread (GUI)**:
   - PyQt5 event loop
   - UI updates
   - Timer callbacks
   - Frame display

2. **StreamReceiver Thread**:
   - FFmpeg subprocess monitoring
   - Frame reading from stdout
   - Queue management
   - Frame dropping logic

### Thread Safety

- **Frame Queue**: Thread-safe Queue from stdlib
- **UI Updates**: Only in main thread (PyQt5 requirement)
- **Callbacks**: Executed in StreamReceiver thread
- **State Variables**: Protected by Python GIL

### Synchronization Points

```
StreamReceiver Thread              Main Thread
─────────────────────              ───────────
Read frame from FFmpeg
       │
Convert to NumPy
       │
Put in queue ─────────────────→ Get from queue
                                      │
                                Display frame
                                      │
                                Write to recorder
```

## Error Handling Strategy

### Levels of Error Handling

1. **Component Level**:
   - Try-catch in each method
   - Return None or False on error
   - Log error details

2. **Application Level**:
   - Callbacks for error notification
   - UI error messages
   - Graceful degradation

3. **System Level**:
   - Logging to file
   - Exception traceback
   - Clean shutdown on fatal errors

### Error Recovery

- **Stream disconnection**: Automatic cleanup, allow reconnect
- **Recording failure**: Stop recording, preserve previous recordings
- **Snapshot failure**: Continue operation, notify user
- **Configuration error**: Fail fast at startup

## Extension Points

### Adding New Features

1. **New Video Filter**:
   - Modify `VideoStreamApp.update_frame()`
   - Apply OpenCV transformations to frame

2. **New Output Format**:
   - Add codec mapping in `Recorder`
   - Update configuration schema

3. **Multi-Stream Support**:
   - Create multiple `StreamReceiver` instances
   - Add stream selector in GUI
   - Coordinate frame display

4. **Audio Support**:
   - Modify FFmpeg command to include audio
   - Add PyAudio for audio playback
   - Sync audio/video frames

5. **Remote Control**:
   - Add network socket in `VideoStreamApp`
   - Implement command protocol
   - Map commands to UI actions

6. **Analytics**:
   - Add frame analysis in `update_frame()`
   - Create analytics overlay
   - Export statistics to CSV

## Performance Considerations

### Latency Optimization

1. **Small buffer size**: Reduce frame queue depth
2. **Frame dropping**: Skip frames if queue is full
3. **Direct frame access**: No frame copying
4. **Efficient display**: Qt optimized image display

### CPU Optimization

1. **No re-encoding**: Use codec 'copy' for recording
2. **Conditional processing**: Only process if needed
3. **Efficient frame conversion**: NumPy zero-copy where possible

### Memory Optimization

1. **Fixed queue size**: Bounded memory usage
2. **Frame reuse**: Frames deleted after processing
3. **No frame buffering**: Stream directly to display

## Configuration Design

### YAML Structure

```yaml
section:
  key: value
  nested:
    key: value
```

### Configuration Loading

1. Parse YAML file
2. Validate required sections
3. Create output directories
4. Build derived values (URLs, commands)

### Configuration Hierarchy

```
config.yaml (file)
     │
     ▼
ConfigManager (parser)
     │
     ▼
Application Components (consumers)
```

## Testing Strategy

### Unit Testing (Recommended)

```python
# Test ConfigManager
def test_config_loading():
    config = ConfigManager('test_config.yaml')
    assert config.get('stream', 'source_ip') == '192.168.100.41'

# Test StreamReceiver
def test_stream_reception():
    receiver = StreamReceiver(mock_ffmpeg_cmd, 1280, 720)
    # Mock FFmpeg output...
    frame = receiver.get_frame()
    assert frame.shape == (720, 1280, 3)

# Test Recorder
def test_recording():
    recorder = Recorder('./test_recordings', 'test_%Y%m%d', 'mp4')
    recorder.start_recording(1280, 720)
    # Write test frames...
    filename = recorder.stop_recording()
    assert os.path.exists(filename)
```

### Integration Testing

1. Test with real FFmpeg stream
2. Test recording full workflow
3. Test snapshot capture
4. Test configuration loading

### Manual Testing Checklist

- [ ] Connect to stream
- [ ] Display video smoothly
- [ ] Start/stop recording
- [ ] Take snapshots
- [ ] Disconnect and reconnect
- [ ] Test with different resolutions
- [ ] Test error scenarios

## Future Enhancements

### Planned Features

1. **Multiple Streams**: View multiple cameras simultaneously
2. **Playback**: Play back recorded videos in app
3. **Motion Detection**: Alert on motion in frame
4. **Cloud Upload**: Automatically upload recordings to cloud
5. **Mobile App**: Companion mobile app for remote viewing
6. **Authentication**: Secure stream access
7. **H.265 Support**: Support newer codecs
8. **Hardware Acceleration**: GPU-accelerated decoding

### Architecture Changes

1. **Plugin System**: Load extensions dynamically
2. **Database**: Store recording metadata
3. **REST API**: Control via HTTP API
4. **WebRTC**: Lower latency streaming
5. **Docker**: Containerized deployment

## Dependencies

### Core Dependencies

- **Python 3.8+**: Language runtime
- **OpenCV (cv2)**: Video processing
- **PyQt5**: GUI framework
- **PyYAML**: Configuration parsing
- **NumPy**: Array operations

### External Dependencies

- **FFmpeg**: Stream reception and decoding

### Dependency Rationale

- **OpenCV**: Industry standard for video processing
- **PyQt5**: Mature, cross-platform GUI framework
- **FFmpeg**: Universal video tool, H.264 support
- **PyYAML**: Standard YAML parser
- **NumPy**: Efficient array operations

## Security Considerations

### Current Implementation

- Local network only (no authentication)
- No encryption (RTP is unencrypted)
- File system access (recordings, snapshots)

### Recommendations for Production

1. **Authentication**: Add stream authentication
2. **Encryption**: Use SRTP instead of RTP
3. **Access Control**: Limit file system access
4. **Input Validation**: Validate configuration values
5. **Network Security**: Firewall rules, VPN

## Maintenance

### Logging

- **File**: `client.log`
- **Format**: Timestamp, level, message
- **Levels**: DEBUG, INFO, WARNING, ERROR

### Monitoring

- FPS counter
- Frame drop statistics
- Queue size
- Connection status

### Debugging

1. Enable DEBUG logging: `--log-level DEBUG`
2. Check `client.log`
3. Monitor statistics in UI
4. Test with FFplay first

## Conclusion

This architecture provides a solid foundation for a video streaming client while remaining simple and extensible. The modular design allows easy addition of new features without major refactoring.
