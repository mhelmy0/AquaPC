# Memory Optimization Guide

## Overview

The RTP Video Streaming Client now features **automatic buffer sizing** that dynamically allocates memory buffers based on your system's available RAM. This optimization can significantly improve streaming performance and reduce frame drops, especially when dealing with high-resolution video streams.

## Feature Details

### What is Auto Buffer Sizing?

Auto buffer sizing automatically calculates and configures optimal buffer sizes for:

1. **Frame Buffer** - Main queue for received video frames
2. **Recording Queue** - Buffer for async video recording
3. **UDP Buffer** - Network receive buffer for RTP packets

By default, the system uses **up to 70% of available RAM** to maximize buffering capacity while leaving enough memory for the operating system and other applications.

### How It Works

The system:
1. Detects total and available system RAM using `psutil`
2. Calculates usable RAM based on configured percentage (default: 70%)
3. Allocates memory across three buffer types:
   - **60%** for main frame buffer
   - **30%** for recording queue
   - **10%** for UDP network buffer
4. Applies safety limits to prevent excessive memory usage
5. Uses optimized buffers automatically throughout the application

### Memory Allocation Example

For a system with **8 GB RAM** and **4 GB available**:

- **Usable RAM**: 4 GB × 70% = 2.8 GB
- **Frame Buffer**: 2.8 GB × 60% = 1.68 GB
  - At 1920×1080 (6.2 MB/frame) = ~270 frames
- **Recording Queue**: 2.8 GB × 30% = 840 MB
  - At 1920×1080 = ~135 frames
- **UDP Buffer**: 2.8 GB × 10% = 280 MB

**Total Allocation**: ~2.8 GB

### Benefits

1. **Reduced Frame Drops** - Larger buffers handle network bursts better
2. **Smoother Playback** - More frames buffered = consistent display
3. **Better Recording** - Larger recording queue prevents blocking
4. **Network Resilience** - Bigger UDP buffer handles packet bursts
5. **Automatic Tuning** - No manual configuration needed

## Configuration

### Enable Auto Buffer Sizing

Edit [config.yaml](config.yaml):

```yaml
advanced:
  auto_buffer_sizing: true      # Enable automatic buffer sizing
  max_ram_usage_percent: 70     # Use up to 70% of free RAM
```

### Disable Auto Buffer Sizing

To use fixed buffer sizes instead:

```yaml
advanced:
  auto_buffer_sizing: false     # Disable automatic buffer sizing
  buffer_size: 1024             # Manual frame buffer size
  recording_queue_size: 100     # Manual recording queue size
  udp_buffer_size: 65536        # Manual UDP buffer size (64KB)
```

### Adjust RAM Usage Percentage

You can adjust how much RAM to use (1-100%):

```yaml
advanced:
  auto_buffer_sizing: true
  max_ram_usage_percent: 50     # Use only 50% of free RAM (more conservative)
```

Or for maximum performance:

```yaml
advanced:
  auto_buffer_sizing: true
  max_ram_usage_percent: 80     # Use up to 80% of free RAM (aggressive)
```

**Recommendations:**
- **Desktop systems**: 70-80%
- **Laptops**: 60-70%
- **Resource-constrained systems**: 40-50%

## Safety Limits

The system enforces safety limits to prevent excessive memory usage:

### Minimum Limits
- Frame buffer: **100 frames**
- Recording queue: **50 frames**
- UDP buffer: **64 KB**

### Maximum Limits
- Frame buffer: **10,000 frames** (~62 GB at 1920×1080)
- Recording queue: **5,000 frames** (~31 GB at 1920×1080)
- UDP buffer: **64 MB**

These limits ensure the system doesn't allocate unreasonable amounts of memory even on systems with very large RAM.

## Memory Usage Monitoring

### GUI Display

When auto buffer sizing is enabled, the application displays real-time RAM usage in the status bar:

```
Status: Connected | FPS: 30.0 | Queue: 45 | RAM: 62.3%
```

This helps you monitor system memory usage while streaming.

### Log Output

At startup, the application logs buffer calculations:

```
2025-10-22 10:30:15,123 - INFO - MemoryManager initialized
2025-10-22 10:30:15,124 - INFO - Frame size: 5.93 MB (1920x1080)
2025-10-22 10:30:15,125 - INFO - Max RAM usage: 70%
2025-10-22 10:30:15,130 - INFO - System RAM - Total: 16384 MB, Available: 8192 MB, Used: 50.0%
2025-10-22 10:30:15,131 - INFO - Usable RAM for buffers: 5734 MB (70%)
2025-10-22 10:30:15,132 - INFO - Calculated optimal buffer sizes:
2025-10-22 10:30:15,132 - INFO -   Frame buffer: 580 frames (3440.5 MB)
2025-10-22 10:30:15,132 - INFO -   Recording queue: 290 frames (1720.3 MB)
2025-10-22 10:30:15,133 - INFO -   UDP buffer: 601554944 bytes (573.7 MB)
2025-10-22 10:30:15,133 - INFO -   Total memory allocation: 5734.5 MB
2025-10-22 10:30:15,133 - INFO -   Percentage of available RAM: 70.0%
```

## Performance Impact

### Resolution Impact

Higher resolutions require more memory per frame:

| Resolution | Bytes/Frame | 1 GB Holds | 10 GB Holds |
|------------|-------------|------------|-------------|
| 640×480    | 0.92 MB     | ~1,087 frames | ~10,870 frames |
| 1280×720   | 2.76 MB     | ~362 frames | ~3,620 frames |
| 1920×1080  | 6.22 MB     | ~161 frames | ~1,610 frames |
| 3840×2160  | 24.88 MB    | ~40 frames | ~402 frames |

### Frame Rate Impact

At 30 FPS:
- **640×480**: 1 GB = ~36 seconds of buffering
- **1280×720**: 1 GB = ~12 seconds of buffering
- **1920×1080**: 1 GB = ~5 seconds of buffering
- **3840×2160**: 1 GB = ~1.3 seconds of buffering

## Troubleshooting

### Issue: Application Uses Too Much RAM

**Solution 1**: Reduce the RAM usage percentage

```yaml
advanced:
  max_ram_usage_percent: 50  # Use less RAM
```

**Solution 2**: Disable auto buffer sizing and use fixed values

```yaml
advanced:
  auto_buffer_sizing: false
  buffer_size: 500
  recording_queue_size: 50
```

### Issue: Still Getting Frame Drops

**Possible causes:**
1. **Insufficient RAM** - System doesn't have enough free RAM
2. **Network issues** - Packet loss exceeds buffer capacity
3. **CPU bottleneck** - Decoding can't keep up with stream

**Solutions:**
1. Close other applications to free RAM
2. Increase RAM usage percentage to 80%
3. Check network quality (WiFi vs Ethernet)
4. Reduce stream resolution on server side

### Issue: psutil Not Installed Error

Auto buffer sizing requires the `psutil` library.

**Install it:**
```bash
pip install psutil
```

Or reinstall all requirements:
```bash
pip install -r requirements.txt
```

## Advanced Usage

### Programmatic Access

You can access the MemoryManager programmatically:

```python
from src.memory_manager import MemoryManager

# Create manager
manager = MemoryManager(
    max_ram_usage_percent=70,
    frame_width=1920,
    frame_height=1080
)

# Get system memory info
mem_info = manager.get_system_memory_info()
print(f"Available RAM: {mem_info['available_mb']} MB")

# Calculate optimal buffers
buffers = manager.calculate_optimal_buffers()
print(f"Frame buffer size: {buffers['frame_buffer_size']} frames")
print(f"Recording queue: {buffers['recording_queue_size']} frames")
print(f"UDP buffer: {buffers['udp_buffer_size']} bytes")

# Check memory health
is_healthy, message = manager.check_memory_health()
print(message)
```

### Custom Buffer Distribution

If you want to modify the buffer distribution (default: 60/30/10), edit [src/memory_manager.py](src/memory_manager.py:118):

```python
# Current distribution:
frame_buffer_bytes = usable_ram_bytes * 0.60    # 60% for frames
recording_buffer_bytes = usable_ram_bytes * 0.30  # 30% for recording
udp_buffer_size = int(usable_ram_bytes * 0.10)   # 10% for UDP

# Example: Prioritize frame buffer over recording
frame_buffer_bytes = usable_ram_bytes * 0.70    # 70% for frames
recording_buffer_bytes = usable_ram_bytes * 0.20  # 20% for recording
udp_buffer_size = int(usable_ram_bytes * 0.10)   # 10% for UDP
```

## Technical Details

### Frame Size Calculation

Each frame uses 3 bytes per pixel (RGB format):

```
Frame size = width × height × 3 bytes
```

Example for 1920×1080:
```
1920 × 1080 × 3 = 6,220,800 bytes = 6.22 MB
```

### Memory Manager Class

Located in [src/memory_manager.py](src/memory_manager.py)

**Key methods:**
- `get_system_memory_info()` - Get RAM stats
- `calculate_optimal_buffers()` - Calculate buffer sizes
- `get_buffer_stats()` - Get current buffer usage
- `check_memory_health()` - Check if RAM is healthy

### Configuration Integration

The [ConfigManager](src/config.py) automatically:
1. Detects if `auto_buffer_sizing` is enabled
2. Calls MemoryManager to calculate buffers
3. Overrides config values with calculated values
4. Provides accessor methods:
   - `get_buffer_size()` - Frame buffer
   - `get_recording_queue_size()` - Recording queue
   - `get_udp_buffer_size()` - UDP buffer

## Comparison: Before vs After

### Before (Fixed Buffers)

```yaml
# Fixed buffer sizes - same on all systems
buffer_size: 1024              # ~6.4 GB at 1920×1080
recording_queue_size: 100      # ~622 MB at 1920×1080
udp_buffer_size: 65536         # 64 KB
```

**Issues:**
- May be too large for systems with little RAM
- May be too small for systems with lots of RAM
- No adaptation to stream resolution
- Manual tuning required

### After (Auto Buffer Sizing)

```yaml
# Automatic buffer sizing
auto_buffer_sizing: true
max_ram_usage_percent: 70
```

**Benefits:**
- Automatically adapts to system RAM
- Scales with video resolution
- No manual configuration needed
- Optimal performance on any system

## Best Practices

1. **Enable auto buffer sizing** for best performance
2. **Use 70% RAM** as starting point (default)
3. **Monitor RAM usage** via GUI status bar
4. **Adjust percentage** based on your workflow:
   - Streaming only: 70-80%
   - Streaming + recording: 60-70%
   - Other apps running: 50-60%
5. **Check logs** on first run to see buffer calculations
6. **Use Ethernet** for best network performance (reduces need for large buffers)

## See Also

- [TROUBLESHOOTING_QUICK_REFERENCE.md](TROUBLESHOOTING_QUICK_REFERENCE.md) - General troubleshooting
- [PACKET_CORRUPTION_FIX.md](PACKET_CORRUPTION_FIX.md) - Network optimization
- [config.yaml](config.yaml) - Configuration file
- [src/memory_manager.py](src/memory_manager.py) - Memory manager source code
