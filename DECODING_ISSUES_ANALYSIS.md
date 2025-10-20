# Decoding Errors & Corrupted Image Analysis

## Issue Report
- **Symptom**: Image displayed is corrupted
- **Error Type**: Decoding errors (to be identified in logs)
- **Impact**: Video stream shows garbled/corrupted frames

## Potential Root Causes

### 1. Frame Size Mismatch 🔴 CRITICAL
**Problem**: Calculated frame size doesn't match actual stream
**Location**: [src/stream_receiver.py](src/stream_receiver.py:195)

```python
frame_size = self.width * self.height * 3  # 3 bytes per pixel (BGR)
```

**Issue**: If resolution configured incorrectly, frames are malformed

**Example**:
- Config says: 1280x720 = 2,764,800 bytes
- Actual stream: 1920x1080 = 6,220,800 bytes
- Result: Incomplete reads, corrupted image

**Solution**:
```yaml
# config.yaml - MUST match server resolution exactly
display:
  width: 1920   # Change to actual resolution
  height: 1080  # Change to actual resolution
```

### 2. SDP Resolution Mismatch 🟡 HIGH
**Problem**: SDP file specifies different resolution than config

**SDP Content** ([config.yaml](config.yaml:14-22)):
```
m=video 5000 RTP/AVP 96
a=rtpmap:96 H264/90000
```

**Missing**: Resolution information in SDP
**Result**: FFmpeg might decode at wrong resolution

**Solution**: Add resolution to SDP or ensure config matches server

### 3. Pixel Format Issues 🟡 MEDIUM
**Problem**: Wrong pixel format for conversion

**Current** ([src/stream_receiver.py](src/stream_receiver.py:266-267)):
```python
frame = np.frombuffer(raw_frame, dtype=np.uint8)
frame = frame.reshape((self.height, self.width, 3))
```

**Assumptions**:
- FFmpeg outputs BGR24 format
- 3 bytes per pixel (8-bit per channel)
- Row-major order

**If any assumption wrong**: Corrupted image

### 4. Incomplete Frame Reads 🔴 CRITICAL
**Problem**: Partial frame data causes corruption

**Current Detection** ([src/stream_receiver.py](src/stream_receiver.py:235-260)):
```python
if len(raw_frame) != frame_size:
    # Incomplete frame
    self.incomplete_frames += 1
```

**Issue**: Even 1 byte short causes complete corruption
**Result**: Entire frame is garbage

### 5. FFmpeg Output Format 🟡 MEDIUM
**Problem**: FFmpeg might not output BGR24 as expected

**Current Command** ([src/config.py](src/config.py:165-166)):
```python
'-f', 'rawvideo',
'-pix_fmt', 'bgr24',
```

**Possible Issues**:
- FFmpeg can't convert to BGR24
- Outputs different format silently
- Platform-specific behavior

## Diagnostic Steps

### Step 1: Verify Resolution
Check what resolution server is actually streaming:

```bash
# On Raspberry Pi
ffprobe rtp://192.168.100.41:5000

# Or check stream.sdp if available
cat /tmp/stream.sdp
```

Look for:
```
a=x-dimensions:1920,1080
```

### Step 2: Test FFmpeg Output
Test FFmpeg decoding manually:

```bash
# Capture 1 frame to file
ffmpeg -protocol_whitelist file,rtp,udp \
  -i rtp://192.168.100.41:5000 \
  -frames:v 1 \
  -f rawvideo \
  -pix_fmt bgr24 \
  test_frame.raw

# Check file size
ls -lh test_frame.raw

# Expected size:
# 1280x720 = 2,764,800 bytes
# 1920x1080 = 6,220,800 bytes
```

### Step 3: Verify Frame Size in Logs
Enable DEBUG logging and check frame sizes:

```yaml
# config.yaml
advanced:
  log_level: "DEBUG"
```

Run application and check logs for:
```
Frame size: X bytes (expected: Y bytes)
```

### Step 4: Check FFmpeg stderr
The new implementation monitors FFmpeg stderr. Check `logs/errors.log` for:
- "Invalid data found"
- "decoding error"
- "corrupt"
- Resolution mismatch warnings

## Common Corruption Patterns

### Pattern 1: Shifted/Offset Image
**Appearance**: Image is there but offset diagonally
**Cause**: Wrong width in reshape()
**Fix**: Correct width in config.yaml

### Pattern 2: Color Distortion
**Appearance**: Colors are wrong (blue sky = red)
**Cause**: Wrong pixel format (RGB vs BGR)
**Fix**: Verify bgr24 format

### Pattern 3: Blocky/Garbled
**Appearance**: Random blocks, noise
**Cause**: Incomplete frames being displayed
**Fix**: Already fixed - now logs and skips incomplete frames

### Pattern 4: Stretched/Squashed
**Appearance**: Image proportions wrong
**Cause**: Width/height swapped or wrong aspect ratio
**Fix**: Check display vs stream resolution

## Fixes to Apply

### Fix 1: Add Resolution Detection 🔴 URGENT

**File**: [src/stream_receiver.py](src/stream_receiver.py:66-117)

Add FFmpeg resolution detection:

```python
def start(self) -> bool:
    # ... existing code ...

    # Start FFmpeg with info output
    self.ffmpeg_process = subprocess.Popen(
        self.ffmpeg_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=10**8
    )

    # Parse stderr for resolution
    self._detect_stream_resolution()

    # ... rest of code ...

def _detect_stream_resolution(self) -> None:
    """Detect actual stream resolution from FFmpeg output"""
    import re

    # Read first few lines of stderr
    for _ in range(20):
        line = self.ffmpeg_process.stderr.readline()
        if not line:
            break

        line = line.decode('utf-8', errors='ignore')

        # Look for: Stream #0:0: Video: h264, yuv420p, 1920x1080
        match = re.search(r'(\d+)x(\d+)', line)
        if match and 'Video' in line:
            detected_width = int(match.group(1))
            detected_height = int(match.group(2))

            if detected_width != self.width or detected_height != self.height:
                self._log_warning(
                    f"Resolution mismatch! Config: {self.width}x{self.height}, "
                    f"Stream: {detected_width}x{detected_height}"
                )

                if self.logger:
                    self.logger.log_error_event(
                        "RESOLUTION_MISMATCH",
                        f"Config: {self.width}x{self.height}, Stream: {detected_width}x{detected_height}",
                        "StreamReceiver"
                    )
            else:
                self._log_info(f"Resolution confirmed: {self.width}x{self.height}")
            break
```

### Fix 2: Validate Frame Data 🟡 IMPORTANT

**File**: [src/stream_receiver.py](src/stream_receiver.py:265-280)

Add frame validation before reshaping:

```python
# Convert raw bytes to numpy array
try:
    frame = np.frombuffer(raw_frame, dtype=np.uint8)

    # Validate buffer size
    expected_size = self.height * self.width * 3
    if frame.size != expected_size:
        self._log_error(
            f"Frame buffer size mismatch: {frame.size} != {expected_size}"
        )
        continue

    # Reshape to image
    frame = frame.reshape((self.height, self.width, 3))

    # Sanity check: values should be 0-255
    if frame.min() < 0 or frame.max() > 255:
        self._log_warning("Frame has invalid pixel values")

except ValueError as e:
    self._log_error(f"Frame reshape error: {e}")
    continue
```

### Fix 3: Add Frame Integrity Check 🟡 MEDIUM

Add checksum or basic validation:

```python
def _validate_frame(self, frame: np.ndarray) -> bool:
    """Validate frame data integrity"""

    # Check shape
    if frame.shape != (self.height, self.width, 3):
        return False

    # Check data type
    if frame.dtype != np.uint8:
        return False

    # Check for all-zero frames (often indicates error)
    if frame.max() == 0:
        self._log_warning("Frame is all black (all zeros)")
        return False

    # Check for unreasonable values
    if frame.std() < 1:  # Very low variance = likely corrupt
        self._log_warning("Frame has very low variance (possibly corrupt)")
        return False

    return True
```

### Fix 4: Enhanced FFmpeg Command 🟡 MEDIUM

**File**: [src/config.py](src/config.py:159-172)

Add more explicit FFmpeg options:

```python
cmd = [
    ffmpeg_path,
    '-protocol_whitelist', 'file,rtp,udp',
    '-i', input_source,
]

if output_format == "rawvideo":
    cmd.extend([
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-vcodec', 'rawvideo',      # Explicit codec
        '-an',                       # No audio
        '-sn',                       # No subtitles
        '-dn',                       # No data streams
        '-'                          # Output to stdout
    ])
```

## Testing Procedure

### 1. Enable Debug Logging
```yaml
# config.yaml
advanced:
  log_level: "DEBUG"
```

### 2. Check Resolution
Run application and immediately check logs:
```bash
tail -f logs/app.log | grep -i "resolution"
```

Should see:
```
Resolution confirmed: 1280x720
```

Or:
```
WARNING: Resolution mismatch! Config: 1280x720, Stream: 1920x1080
```

### 3. Monitor Frame Quality
```bash
tail -f logs/warnings.log
```

Look for:
- "Frame has invalid pixel values"
- "Frame is all black"
- "Frame reshape error"

### 4. Check FFmpeg Errors
```bash
tail -f logs/errors.log | grep -i "decode"
```

Look for:
- "decoding error"
- "Invalid data"
- "corrupt"

## Quick Fixes to Try

### Fix A: Update Resolution in Config
```yaml
# config.yaml
display:
  width: 1920   # Try actual server resolution
  height: 1080
```

### Fix B: Test with Lower Resolution
If server streams 1920x1080 but you configured 1280x720:

```yaml
# On Raspberry Pi - reduce resolution
# Modify server command to stream 1280x720
```

### Fix C: Force Resolution in FFmpeg
Add explicit scaling:

```python
# In config.py get_ffmpeg_command()
if output_format == "rawvideo":
    cmd.extend([
        '-vf', f'scale={self.width}:{self.height}',  # Force scale
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-'
    ])
```

## Expected Log Output (Good)

```
2025-10-20 23:30:00 - StreamReceiver - INFO - Stream receiver started
2025-10-20 23:30:01 - StreamReceiver - INFO - Resolution confirmed: 1280x720
2025-10-20 23:30:01 - StreamReceiver - INFO - Frames received: 30 (1s)
2025-10-20 23:30:02 - StreamReceiver - INFO - Frames received: 60 (2s)
```

## Expected Log Output (Bad - Resolution Mismatch)

```
2025-10-20 23:30:00 - StreamReceiver - INFO - Stream receiver started
2025-10-20 23:30:01 - StreamReceiver - WARNING - Resolution mismatch! Config: 1280x720, Stream: 1920x1080
2025-10-20 23:30:01 - StreamReceiver - ERROR - Frame reshape error: cannot reshape array of size 6220800 into shape (720,1280,3)
2025-10-20 23:30:02 - StreamReceiver - WARNING - Incomplete frame received: 2764800/6220800 bytes
```

## Action Items

1. ⚠️ **IMMEDIATE**: Check what resolution server is streaming
2. ⚠️ **IMMEDIATE**: Update config.yaml to match server resolution
3. 📝 **RECOMMENDED**: Implement resolution detection (Fix 1)
4. 📝 **RECOMMENDED**: Add frame validation (Fix 2)
5. 🔍 **DEBUG**: Enable DEBUG logging and capture full session

## Files to Check

1. **config.yaml** - Verify width/height match server
2. **logs/errors.log** - Look for decode errors
3. **logs/warnings.log** - Look for frame validation warnings
4. **Server SDP file** - Check actual resolution

---

**Status**: Analysis complete, awaiting server resolution confirmation
**Next Step**: Verify actual server resolution and update config
**Risk**: HIGH if resolution mismatch, LOW if config correct
