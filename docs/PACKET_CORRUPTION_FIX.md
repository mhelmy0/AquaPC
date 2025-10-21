# Packet Corruption & Decoding Errors - Analysis & Fixes

## Issues Detected

### ✅ Resolution: FIXED
```
✅ Resolution confirmed: 1920x1080
```
**Status**: Working correctly!

### ❌ Packet Corruption: ACTIVE ISSUE
```
❌ FFmpeg: Packet corruption detected (multiple occurrences)
❌ error while decoding MB (macroblock errors)
❌ concealing XXXX DC, AC, MV errors in P/I frame
```
**Status**: High packet loss on network

## Root Cause Analysis

### The Problem

**Symptom**: Frequent decoding errors in logs:
```
[h264 @ XXX] error while decoding MB 14 67, bytestream -5
[h264 @ XXX] concealing 155 DC, 155 AC, 155 MV errors in P frame
```

**Meaning**:
- **MB (Macroblock)**: 16x16 pixel block in H.264
- **bytestream -5/-7/-14**: Bytes missing from packet
- **Concealing errors**: FFmpeg tries to hide corruption by copying from previous frames
- **P frame**: Predictive frame (depends on previous frames)
- **I frame**: Independent frame (can decode standalone)

### Why This Happens

1. **UDP Protocol** - No retransmission
   - RTP uses UDP (unreliable)
   - Lost packets = lost data forever
   - No automatic recovery

2. **Network Issues**:
   - WiFi interference/distance
   - Network congestion
   - Router buffer overflow
   - Bandwidth saturation

3. **High Bitrate** (1920x1080 @ 30fps):
   - Bitrate: ~4-8 Mbps observed
   - Packet rate: ~1000-2000 packets/sec
   - More packets = more opportunities for loss

## Impact on Video Quality

### What You're Seeing:
- ✅ Video displays (not crashing)
- ⚠️ Some frames have artifacts/blocks
- ⚠️ Occasional freezing/skipping
- ⚠️ Color distortion in areas

### FFmpeg is Recovering:
```
concealing XXXX errors
```
FFmpeg tries to hide corruption, but:
- Large errors (7000+) = very noticeable
- Small errors (100-500) = minor artifacts

## Solutions

### Quick Fixes (Try These First)

#### 1. Use Wired Connection ⭐ BEST FIX
```bash
# Instead of WiFi:
- Connect Raspberry Pi via Ethernet cable
- Connect PC via Ethernet cable

Expected: 90-99% packet loss reduction
```

#### 2. Reduce Stream Resolution on Server
```bash
# On Raspberry Pi, stream at 720p instead of 1080p:
# Reduces bandwidth by ~50%

# Then update client config.yaml:
display:
  width: 1280
  height: 720
```

#### 3. Reduce Frame Rate
```bash
# On Raspberry Pi, reduce from 30fps to 20fps
# Reduces bandwidth by ~33%
```

#### 4. Lower Bitrate
```bash
# On Raspberry Pi FFmpeg command, add:
-b:v 3000k  # Reduce from 6000k to 3000k
```

### Advanced Fixes

#### Fix 1: Improve WiFi Signal

**If must use WiFi**:
- Move Raspberry Pi closer to router
- Use 5GHz WiFi instead of 2.4GHz
- Reduce WiFi interference (move microwave, cordless phones)
- Use WiFi extender/better router

#### Fix 2: Enable Error Concealment in FFmpeg

**Update FFmpeg command** ([src/config.py](src/config.py:159-172)):

```python
cmd = [
    ffmpeg_path,
    '-protocol_whitelist', 'file,rtp,udp',
    '-fflags', '+genpts+igndts',      # Generate timestamps, ignore DTS
    '-err_detect', 'ignore_err',       # Ignore errors, continue decoding
    '-i', input_source,
]

if output_format == "rawvideo":
    cmd.extend([
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-vf', 'setpts=PTS-STARTPTS',  # Reset timestamps
        '-'
    ])
```

#### Fix 3: Increase UDP Buffer Size

**Update config.yaml**:
```yaml
advanced:
  udp_buffer_size: 65536  # Increase from default (new setting)
```

**Update FFmpeg command**:
```python
cmd = [
    ffmpeg_path,
    '-protocol_whitelist', 'file,rtp,udp',
    '-buffer_size', '65536',           # 64KB buffer
    '-i', input_source,
]
```

#### Fix 4: Use Different Protocol (SRT instead of RTP)

**On Server** (if supported):
```bash
# SRT has built-in error correction
ffmpeg -f h264 -i - -c:v copy -f mpegts srt://192.168.100.41:5000
```

**On Client**:
```bash
# Requires libsrt
ffmpeg -i srt://192.168.100.41:5000 ...
```

### Configuration Updates

#### Update config.yaml

Add these settings:

```yaml
# Advanced settings
advanced:
  # Existing settings...

  # Packet loss mitigation
  ignore_decode_errors: true    # Don't stop on decode errors
  error_concealment: true        # Let FFmpeg conceal errors
  udp_buffer_size: 65536        # Larger UDP buffer (64KB)

  # Frame validation (already added)
  validate_every_n_frames: 30   # Only validate every 30th frame
```

## Testing & Verification

### Check Packet Loss

```powershell
# While streaming, check stats in logs
Select-String -Path logs\warnings.log -Pattern "Packet corrupt" | Measure-Object

# Count MB decode errors
Select-String -Path logs\errors.log -Pattern "error while decoding MB" | Measure-Object
```

### Calculate Packet Loss Rate

```powershell
# Get error count over time period
$errors = Select-String -Path logs\errors.log -Pattern "concealing"
$errors.Count  # Total errors

# If streaming for 1 minute at 30fps:
# 30 fps × 60 sec = 1800 frames
# If 50 errors, that's ~2.7% frame corruption rate
```

### Network Quality Test

```bash
# Ping Raspberry Pi
ping 192.168.100.41 -t

# Look for:
# - Latency < 5ms (excellent)
# - 0% packet loss (required)
# - Consistent response time
```

## Monitoring

### Watch for These Patterns

**Good (Low Error Rate)**:
```
# Few errors per minute
[h264] concealing 100-500 errors  # Minor artifacts
Packet corruption: 1-2 per minute
```

**Bad (High Error Rate)**:
```
# Many errors per second
[h264] concealing 5000-7000 errors  # Major artifacts
Packet corruption: 10+ per minute
```

### Check FFmpeg Stats

Look for this in logs:
```
frame= 169 fps= 10 q=-0.0 size= 1020600KiB time=00:00:05.90
  bitrate=1417077.2kbits/s dup=77 drop=5 speed=0.4
```

**Key metrics**:
- `drop=5` - Dropped frames (network loss)
- `dup=77` - Duplicated frames (compensating for loss)
- High dup/drop ratio = packet loss issue

## Temporary Workaround

### Reduce Logging Verbosity

The errors are being logged but FFmpeg is handling them. To reduce log spam:

**Update config.yaml**:
```yaml
advanced:
  log_level: "WARNING"  # Only log warnings and errors, not every decode error
  suppress_decode_errors: true  # New setting
```

This won't fix packet loss, but will make logs cleaner.

## Expected Results After Fixes

### With Wired Connection:
- ✅ <1% packet loss
- ✅ Few or no decode errors
- ✅ Clean, smooth video
- ✅ Minimal log errors

### With WiFi Optimization:
- ⚠️ 1-5% packet loss (acceptable)
- ⚠️ Some minor artifacts
- ✅ Watchable video
- ⚠️ Some log errors (ignorable)

### With Reduced Quality:
- ✅ Lower bandwidth requirement
- ✅ Fewer packet loss issues
- ⚠️ Lower resolution/quality
- ✅ More reliable stream

## Server-Side Fixes (Raspberry Pi)

### Reduce Bitrate
```bash
# In server FFmpeg command, add:
-b:v 3000k       # Reduce from 6000k
-maxrate 3500k   # Set max bitrate
-bufsize 6000k   # Buffer size
```

### Enable FEC (Forward Error Correction)
```bash
# If supported by your setup:
-fec prompeg=l=4:d=4  # Adds redundancy
```

### Use Smaller Packets
```bash
# Already using -pkt_size 1200, which is good
# Can try smaller: -pkt_size 1000
```

### Add I-Frames More Frequently
```bash
# Make recovery faster after packet loss:
-g 30  # I-frame every 30 frames (every second at 30fps)
```

## Network Optimization

### Router Settings
1. **Enable QoS** (Quality of Service)
   - Prioritize UDP port 5000
   - Prioritize Raspberry Pi MAC address

2. **Dedicated WiFi Channel**
   - Use least congested channel
   - Use 5GHz if available

3. **Disable Power Saving**
   - On Raspberry Pi WiFi
   - On PC WiFi

### System-Level Fixes

**On Raspberry Pi**:
```bash
# Disable WiFi power management
sudo iwconfig wlan0 power off

# Increase network buffer
sudo sysctl -w net.core.rmem_max=26214400
sudo sysctl -w net.core.rmem_default=26214400
```

**On Windows PC**:
```powershell
# Increase receive buffer (run as Administrator)
netsh int udp set global recvbufferthreshold=524288
```

## Summary

### Current Status
- ✅ **Resolution**: FIXED (1920x1080 confirmed)
- ✅ **Stream Connection**: Working
- ✅ **Recording**: Working (74.9 MB recorded successfully)
- ❌ **Packet Loss**: HIGH (causing decode errors)

### Root Cause
- **Network quality issue** (likely WiFi)
- UDP packet loss (no retransmission)
- High bitrate (1.4 Mbps observed, spikes to 1.4 Gbps!)

### Recommended Actions (Priority Order)

1. **🔴 CRITICAL**: Switch to wired Ethernet (both devices)
2. **🟡 IMPORTANT**: If WiFi required, optimize signal/router
3. **🟢 OPTIONAL**: Reduce stream quality (720p @ 20fps)
4. **🟢 OPTIONAL**: Update FFmpeg command for error resilience

### What's Working Despite Errors

The application is actually handling packet loss well:
- ✅ Video displays (not crashing)
- ✅ FFmpeg conceals errors automatically
- ✅ Recording completes successfully
- ✅ Auto-reconnect working (reconnected after incomplete frame)

**The errors are logged but the app continues working!**

### Next Steps

1. **Test with wired connection** (if possible)
2. **Monitor packet loss** over longer period
3. **Reduce stream quality** if wired not possible
4. **Accept minor artifacts** if quality is acceptable

---

**Status**: Stream is functional but has packet corruption
**Impact**: Minor to moderate video artifacts
**Fix**: Use wired Ethernet or reduce stream quality
**Urgency**: LOW (app works, video watchable with artifacts)
