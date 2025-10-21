# Low Latency Streaming Guide

## Problem: High Delay and Frame Corruption

If you're experiencing:
- **High latency** (10-20 second delay between live and display)
- **Frame corruption** after a few minutes
- **Choppy playback** with stuttering

This guide will help you achieve **near real-time streaming** with minimal delay.

## Root Causes

### 1. Excessive Buffering
- Default auto buffer sizing allocates **up to 70% of RAM**
- With 8GB available RAM: ~515 frames buffered = **17+ seconds delay!**
- You're watching old video, not a live stream

### 2. CPU Decoding Bottleneck
- FFmpeg uses **software CPU decoding** by default (slow)
- H.264 decoding at 1920×1080 @ 30fps is CPU-intensive
- Processing can't keep up → frames queue up → corruption

### 3. Inefficient Frame Dropping
- `frame_drop_threshold: 10` drops frames when queue > 10
- But buffer holds 500+ frames → old frames accumulate
- Queue fills faster than it empties

## Solution: Low Latency Mode

The application now includes **3 performance modes**:

| Mode | Latency | Buffer Size | Use Case |
|------|---------|-------------|----------|
| **low_latency** | ~0.5-1s | 3 frames | Real-time monitoring, live events |
| **balanced** | ~3-5s | 90 frames | General use, some delay acceptable |
| **high_quality** | ~10-20s | 600+ frames | Recording, quality over latency |

## Quick Fix: Enable Low Latency Mode

### Step 1: Edit config.yaml

```yaml
advanced:
  # Change this to low_latency
  performance_mode: "low_latency"

  # Enable GPU hardware acceleration
  hw_accel: "auto"
```

### Step 2: Restart Application

```bash
python main.py
```

### Step 3: Check Status Bar

You should now see:
```
Status: Connected | FPS: 30.0 | Queue: 2 | Latency: ~67ms | Mode: LL | GPU: auto
```

**Latency should be under 1 second!**

## Performance Mode Details

### Low Latency Mode (Recommended for Real-Time)

**Settings:**
```yaml
advanced:
  performance_mode: "low_latency"
  hw_accel: "auto"
```

**Configuration:**
- Buffer size: **3 frames** (~100ms at 30fps)
- Frame drop threshold: **2** (aggressive dropping)
- RAM usage: **10%** (minimal memory)
- Auto buffer sizing: **Disabled**
- Recording queue: **30 frames** (1 second)

**Benefits:**
- ✅ Minimal delay (0.5-1 second)
- ✅ GPU hardware acceleration
- ✅ Real-time monitoring
- ✅ Responsive to stream changes

**Trade-offs:**
- ⚠️ May drop frames during network bursts
- ⚠️ Less resilient to packet loss
- ⚠️ Recording may have some drops

**Best for:**
- Live monitoring applications
- Security cameras
- Real-time events
- Interactive scenarios

### Balanced Mode (Default)

**Settings:**
```yaml
advanced:
  performance_mode: "balanced"
  hw_accel: "auto"
```

**Configuration:**
- Buffer size: **90 frames** (~3s at 30fps)
- Frame drop threshold: **30**
- RAM usage: **30%**
- Recording queue: **150 frames** (5 seconds)

**Benefits:**
- ✅ Moderate latency (3-5 seconds)
- ✅ Good network resilience
- ✅ Smooth playback
- ✅ Reliable recording

**Best for:**
- General purpose streaming
- Scenarios where some delay is acceptable
- Networks with moderate packet loss

### High Quality Mode

**Settings:**
```yaml
advanced:
  performance_mode: "high_quality"
  hw_accel: "auto"
```

**Configuration:**
- Buffer size: **600 frames** (~20s at 30fps)
- Frame drop threshold: **200**
- RAM usage: **70%** (uses auto buffer sizing)
- Recording queue: **300 frames** (10 seconds)

**Benefits:**
- ✅ Maximum quality
- ✅ Handles network issues well
- ✅ Smooth, consistent playback
- ✅ High-quality recordings

**Trade-offs:**
- ⚠️ High latency (10-20 seconds)
- ⚠️ Large memory usage
- ⚠️ Not suitable for real-time monitoring

**Best for:**
- High-quality recording sessions
- Poor network conditions
- When quality matters more than latency

## GPU Hardware Acceleration

### Why Use GPU Acceleration?

**CPU Software Decoding:**
- Uses general-purpose CPU cores
- Slow for high-resolution video (1920×1080)
- Can cause 100% CPU usage
- Bottleneck at ~20-30 FPS

**GPU Hardware Decoding:**
- Uses dedicated video decode hardware (NVDEC, DXVA2, Quick Sync)
- 5-10x faster than CPU
- <10% CPU usage
- Handles 4K @ 60fps easily

### Supported Hardware

#### NVIDIA GPUs (NVDEC)
- GTX 600 series and newer
- Uses **CUDA** or **cuvid** acceleration
- Best performance

```yaml
advanced:
  hw_accel: "cuda"  # or "auto"
```

#### AMD GPUs (AMF/DXVA2)
- Radeon HD 7000 series and newer
- Uses **DXVA2** on Windows

```yaml
advanced:
  hw_accel: "dxva2"  # or "auto"
```

#### Intel GPUs (Quick Sync)
- Intel HD Graphics 2000 and newer
- Uses **qsv** (Quick Sync Video)

```yaml
advanced:
  hw_accel: "qsv"  # or "auto"
```

#### Auto-Detection (Recommended)
```yaml
advanced:
  hw_accel: "auto"  # Let FFmpeg choose best option
```

### Check GPU Acceleration

After starting the stream, check the logs:

```bash
# Windows PowerShell
Get-Content logs/app.log -Tail 50 | Select-String "hwaccel"
```

You should see FFmpeg using hardware acceleration in the command.

## Latency Monitoring

The status bar now shows **real-time latency**:

```
Status: Connected | FPS: 30.0 | Queue: 2 | Latency: ~67ms | Mode: LL | GPU: auto
```

**Latency calculation:**
```
Latency (seconds) = Queue Size / FPS
Latency (seconds) = 2 frames / 30 fps = 0.067s = 67ms
```

**Target Latencies:**
- **Low Latency Mode**: < 1 second (queue < 30)
- **Balanced Mode**: 3-5 seconds (queue 90-150)
- **High Quality Mode**: 10-20 seconds (queue 300-600)

If latency is too high:
1. Switch to lower latency mode
2. Enable GPU acceleration
3. Check network quality
4. Reduce stream resolution on server

## Troubleshooting

### Issue 1: Still High Latency Despite Low Latency Mode

**Check configuration:**
```bash
python -c "from src.config import ConfigManager; c = ConfigManager(); print(f'Mode: {c.get(\"advanced\", \"performance_mode\")}'); print(f'Buffer: {c.get_buffer_size()}'); print(f'Threshold: {c.get(\"advanced\", \"frame_drop_threshold\")}')"
```

**Expected output:**
```
Mode: low_latency
Buffer: 3
Threshold: 2
```

**If different:** Delete config overrides and restart.

### Issue 2: GPU Acceleration Not Working

**Verify GPU support:**
```bash
ffmpeg -hwaccels
```

**Should show:**
```
Hardware acceleration methods:
cuda
dxva2
qsv
d3d11va
```

**If missing:** Update FFmpeg or drivers.

**Try specific acceleration:**
```yaml
# For NVIDIA
hw_accel: "cuda"

# For AMD/Windows
hw_accel: "dxva2"

# For Intel
hw_accel: "qsv"
```

### Issue 3: Frame Corruption/Artifacts

**Causes:**
- Network packet loss (not enough buffering)
- GPU decoding errors
- Stream quality issues

**Solutions:**

**1. Switch to balanced mode** (more buffering):
```yaml
performance_mode: "balanced"
```

**2. Disable GPU acceleration temporarily:**
```yaml
hw_accel: "none"
```

**3. Increase error tolerance:**
```yaml
ignore_decode_errors: true
udp_buffer_size: 131072  # Increase to 128KB
```

**4. Use wired Ethernet instead of WiFi**

### Issue 4: Recording Has Dropped Frames

**Low latency mode has small recording queue** (30 frames).

**Solutions:**

**Option 1:** Use balanced mode when recording:
```yaml
performance_mode: "balanced"  # 150 frame recording queue
```

**Option 2:** Manually increase recording queue:
```yaml
performance_mode: "low_latency"
recording_queue_size: 150  # Override for recording
```

**Option 3:** Record on server side instead of client

### Issue 5: High CPU Usage Even with GPU Acceleration

**Check if GPU is actually being used:**

**Windows Task Manager:**
1. Open Task Manager (Ctrl+Shift+Esc)
2. Go to "Performance" tab
3. Select your GPU
4. Check "Video Decode" usage (should be >0%)

**If GPU decode is 0%:** GPU acceleration failed, FFmpeg falling back to CPU.

**Fix:**
1. Update graphics drivers
2. Update FFmpeg to latest version
3. Try specific hw_accel instead of "auto"

## Advanced Optimization

### Custom Performance Profile

Create your own profile in [config.yaml](config.yaml):

```yaml
advanced:
  # Custom ultra-low latency (< 500ms)
  performance_mode: "balanced"  # Use as base
  buffer_size: 2                # Override: only 2 frames
  frame_drop_threshold: 1       # Override: drop aggressively
  auto_buffer_sizing: false
  recording_queue_size: 20

  # Use GPU
  hw_accel: "cuda"  # or "dxva2", "qsv"

  # Ultra low latency FFmpeg flags (automatically applied in low_latency mode)
  # These are set programmatically, no need to configure
```

### Server-Side Optimization

For best results, optimize the stream on the Raspberry Pi server:

**1. Reduce encoding latency:**
```bash
# Add these flags to your server's FFmpeg command:
-tune zerolatency      # H.264 zero latency tune
-preset ultrafast      # Fast encoding
-g 30                  # GOP size = framerate (reduce keyframe interval)
-bf 0                  # No B-frames
```

**2. Reduce resolution if needed:**
```bash
# 720p instead of 1080p
-s 1280x720

# Or lower bitrate
-b:v 2M
```

**3. Use lower framerate if acceptable:**
```bash
-r 15  # 15 FPS instead of 30
```

## Comparison: Before vs After

### Before (Default Settings)
```yaml
performance_mode: "high_quality"  # or undefined
auto_buffer_sizing: true
max_ram_usage_percent: 70
hw_accel: "none"
```

**Result:**
- Queue: 515 frames
- Latency: ~17 seconds
- CPU usage: 80-100%
- GPU usage: 0%
- Frame corruption after minutes

### After (Low Latency Settings)
```yaml
performance_mode: "low_latency"
hw_accel: "auto"
```

**Result:**
- Queue: 2-3 frames
- Latency: ~100ms (0.1 seconds)
- CPU usage: 10-20%
- GPU usage: 30-50% (decode engine)
- Smooth, real-time playback

## Performance Metrics

### Expected Performance by Mode

| Mode | Queue Size | Latency | CPU Usage | Memory | Frame Drops |
|------|-----------|---------|-----------|--------|-------------|
| Low Latency | 2-3 | 67-100ms | 10-20% | 20 MB | Some |
| Balanced | 30-90 | 1-3s | 15-30% | 500 MB | Few |
| High Quality | 300-600 | 10-20s | 20-40% | 3.5 GB | None |

*CPU usage assumes GPU acceleration enabled*

## Best Practices

### For Real-Time Monitoring

1. **Use low latency mode**
   ```yaml
   performance_mode: "low_latency"
   ```

2. **Enable GPU acceleration**
   ```yaml
   hw_accel: "auto"
   ```

3. **Use wired Ethernet** (not WiFi)

4. **Monitor latency** in status bar

5. **Accept some frame drops** for lowest latency

### For High-Quality Recording

1. **Use balanced or high quality mode**
   ```yaml
   performance_mode: "balanced"
   ```

2. **Enable GPU acceleration** (reduces CPU load)
   ```yaml
   hw_accel: "auto"
   ```

3. **Use high-quality network** (Ethernet)

4. **Monitor queue size** (should stay below threshold)

### For Poor Network Conditions

1. **Use balanced mode** (more buffering)
   ```yaml
   performance_mode: "balanced"
   ```

2. **Increase UDP buffer**
   ```yaml
   udp_buffer_size: 262144  # 256KB
   ```

3. **Enable error tolerance**
   ```yaml
   ignore_decode_errors: true
   ```

4. **Consider reducing server stream quality**

## Summary

**To achieve low latency (<1 second):**

1. Set `performance_mode: "low_latency"` in [config.yaml](config.yaml)
2. Set `hw_accel: "auto"` for GPU acceleration
3. Restart application
4. Check status bar for latency indicator
5. Optimize server stream if needed

**Current status bar should show:**
```
Status: Connected | Queue: 2-3 | Latency: ~100ms | Mode: LL | GPU: auto
```

**If latency is still high:** Check network, update drivers, verify GPU support.

## See Also

- [MEMORY_OPTIMIZATION.md](MEMORY_OPTIMIZATION.md) - Buffer sizing details
- [TROUBLESHOOTING_QUICK_REFERENCE.md](TROUBLESHOOTING_QUICK_REFERENCE.md) - General troubleshooting
- [PACKET_CORRUPTION_FIX.md](PACKET_CORRUPTION_FIX.md) - Network issues
- [config.yaml](config.yaml) - Configuration file
