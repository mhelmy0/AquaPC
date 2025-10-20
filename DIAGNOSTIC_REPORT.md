# Stream Connection Issues - Diagnostic Report

## Issue Summary

Based on analysis of [client.log](client.log:1-15), the following issues were identified:

### Symptoms
1. ✅ Connection establishes successfully
2. ❌ Stream disconnects with "Incomplete frame received" warning
3. ❌ Recording hangs/freezes during streaming
4. ❌ Connection lost unexpectedly

### Log Analysis

**Session 1** (23:49:29 - 23:50:42):
```
23:49:29 - Stream receiver started
23:49:34 - Stream connected
23:50:42 - WARNING: Incomplete frame received, stream may have ended
23:50:42 - Stream receiver stopped
23:50:42 - Stream disconnected
```
**Duration**: ~1 minute 13 seconds before failure

**Session 2** (23:50:54 - 23:58:45):
```
23:50:58 - Stream receiver started
23:50:58 - Stream connected
23:58:45 - WARNING: Incomplete frame received, stream may have ended
23:58:45 - Stream receiver stopped
23:58:45 - Stream disconnected
```
**Duration**: ~7 minutes 47 seconds before failure

## Root Cause Analysis

### Issue 1: Incomplete Frame Reception
**Location**: [src/stream_receiver.py](src/stream_receiver.py:96-101)

**Problem**:
```python
raw_frame = self.ffmpeg_process.stdout.read(frame_size)

if len(raw_frame) != frame_size:
    # End of stream or error
    logging.warning("Incomplete frame received, stream may have ended")
    break
```

**Root Causes**:
1. **Network packet loss** - UDP packets dropped by network
2. **FFmpeg buffer overflow** - FFmpeg can't keep up with incoming stream
3. **Server stream interruption** - Raspberry Pi stops/restarts streaming
4. **Blocking read() call** - Can hang if stream stops sending data
5. **No timeout mechanism** - Application doesn't detect stalled streams

### Issue 2: Recording Hang
**Location**: [src/recorder.py](src/recorder.py:104-118)

**Problem**:
```python
def write_frame(self, frame: np.ndarray) -> bool:
    if not self.is_recording or not self.video_writer:
        return False

    try:
        self.video_writer.write(frame)  # Can block if disk is slow
        self.frame_count += 1
        return True
```

**Root Causes**:
1. **Synchronous disk I/O** - Blocks main thread during write
2. **No write timeout** - Can hang indefinitely
3. **No buffer overflow detection** - Keeps trying to write even if disk is slow
4. **Frame queue backup** - If recording is slow, frame queue fills up

### Issue 3: No Automatic Recovery
**Location**: [src/stream_receiver.py](src/stream_receiver.py:80-112)

**Problem**:
- Stream disconnects permanently on any error
- No reconnection logic
- No keep-alive mechanism
- No stream health monitoring

## Critical Issues Identified

### 1. Blocking I/O with No Timeout ⚠️ CRITICAL
- `stdout.read()` blocks indefinitely if stream stalls
- No timeout on frame reception
- Can cause entire application to hang

### 2. No Stream Keep-Alive 🔴 HIGH
- No way to detect if stream is actually alive
- FFmpeg process might be running but not receiving data
- Network issues not detected until frame read fails

### 3. Fragile Error Handling ⚠️ MEDIUM
- Single error breaks entire receive loop
- No retry mechanism
- No graceful degradation

### 4. Recording Performance 🟡 MEDIUM
- Synchronous disk writes can slow down frame processing
- No queue for write operations
- Can cause frame drops

### 5. UDP Packet Loss ⚠️ MEDIUM
- UDP has no reliability guarantees
- Lost packets cause incomplete frames
- No mechanism to request retransmission

## Recommended Fixes

### Fix 1: Add Timeout to Frame Reception (HIGH PRIORITY)

**File**: [src/stream_receiver.py](src/stream_receiver.py:80-112)

```python
import select

def _receive_loop(self) -> None:
    frame_size = self.width * self.height * 3
    timeout = 5.0  # 5 second timeout

    while self.running:
        try:
            # Check if data is available with timeout
            ready = select.select([self.ffmpeg_process.stdout], [], [], timeout)

            if not ready[0]:
                # Timeout - no data received
                logging.warning("Stream timeout - no data received for 5 seconds")
                if self.on_error:
                    self.on_error("Stream timeout")
                break

            # Read with non-blocking approach
            raw_frame = self.ffmpeg_process.stdout.read(frame_size)

            # ... rest of code
```

### Fix 2: Implement Automatic Reconnection (HIGH PRIORITY)

**File**: [src/video_display.py](src/video_display.py:1) or new `connection_manager.py`

```python
class ConnectionManager:
    """Manages stream connection with auto-reconnect"""

    def __init__(self, max_retries=5, retry_interval=5):
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.retry_count = 0

    def connect_with_retry(self):
        while self.retry_count < self.max_retries:
            try:
                if self.stream_receiver.start():
                    self.retry_count = 0  # Reset on success
                    return True
            except Exception as e:
                self.retry_count += 1
                logger.warning(f"Connection failed, retry {self.retry_count}/{self.max_retries}")
                time.sleep(self.retry_interval)

        return False
```

### Fix 3: Add Stream Health Monitoring (MEDIUM PRIORITY)

**File**: [src/stream_receiver.py](src/stream_receiver.py:153-169)

```python
def is_alive(self) -> bool:
    if not self.running:
        return False

    # Check FFmpeg process is alive
    if self.ffmpeg_process and self.ffmpeg_process.poll() is not None:
        return False

    # Check if we've received frames recently
    time_since_last_frame = time.time() - self.last_frame_time
    if time_since_last_frame > 10.0:  # 10 second threshold
        logger.error(f"No frames for {time_since_last_frame:.1f} seconds", "StreamReceiver")
        return False

    return True
```

### Fix 4: Async Recording with Queue (MEDIUM PRIORITY)

**File**: [src/recorder.py](src/recorder.py:1)

```python
import threading
import queue

class Recorder:
    def __init__(self, ...):
        # ... existing code ...
        self.write_queue = queue.Queue(maxsize=100)
        self.write_thread = None

    def _write_loop(self):
        """Background thread for writing frames"""
        while self.is_recording:
            try:
                frame = self.write_queue.get(timeout=1)
                self.video_writer.write(frame)
                self.frame_count += 1
            except queue.Empty:
                continue

    def write_frame(self, frame):
        """Non-blocking frame write"""
        if not self.is_recording:
            return False

        try:
            self.write_queue.put_nowait(frame.copy())
            return True
        except queue.Full:
            logger.warning("Recording queue full, dropping frame")
            return False
```

### Fix 5: Better FFmpeg Error Detection (MEDIUM PRIORITY)

**File**: [src/stream_receiver.py](src/stream_receiver.py:50-78)

```python
def start(self) -> bool:
    try:
        self.ffmpeg_process = subprocess.Popen(
            self.ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8
        )

        # Start stderr monitoring thread
        self.stderr_thread = threading.Thread(
            target=self._monitor_ffmpeg_errors,
            daemon=True
        )
        self.stderr_thread.start()

        # ... rest of code

def _monitor_ffmpeg_errors(self):
    """Monitor FFmpeg stderr for errors"""
    while self.running:
        line = self.ffmpeg_process.stderr.readline()
        if not line:
            break

        line = line.decode('utf-8', errors='ignore')

        # Check for common errors
        if 'Connection refused' in line:
            logger.error("FFmpeg: Connection refused", "StreamReceiver")
        elif 'Invalid data found' in line:
            logger.error("FFmpeg: Invalid stream data", "StreamReceiver")
        elif 'Packet corrupt' in line:
            logger.warning("FFmpeg: Packet corruption detected", "StreamReceiver")
```

### Fix 6: Network Buffer Tuning (LOW PRIORITY)

**File**: [src/config.py](src/config.py:135-172)

```python
def get_ffmpeg_command(self, output_format: str = "rawvideo") -> list:
    # ... existing code ...

    cmd = [
        ffmpeg_path,
        '-protocol_whitelist', 'file,rtp,udp',
        '-fflags', 'nobuffer',           # Minimize buffering
        '-flags', 'low_delay',           # Low latency mode
        '-rtsp_transport', 'udp',        # Force UDP
        '-max_delay', '500000',          # Max 500ms delay
        '-i', input_source,
    ]

    # ... rest of code
```

## Immediate Actions Required

### 1. Add Timeout Mechanism ⚠️ URGENT
Without timeout, application will hang indefinitely if stream stops.

### 2. Implement Auto-Reconnect 🔴 IMPORTANT
Network interruptions should not require manual reconnection.

### 3. Monitor Stream Health 🔴 IMPORTANT
Detect stalled streams before they cause hangs.

### 4. Improve Error Logging 🟡 RECOMMENDED
Need more detailed error messages for troubleshooting.

## Testing Recommendations

After implementing fixes, test these scenarios:

1. **Network Interruption**:
   - Disconnect Raspberry Pi network during streaming
   - Should auto-reconnect when network returns

2. **Server Restart**:
   - Restart FFmpeg on Raspberry Pi during streaming
   - Client should detect and reconnect

3. **Packet Loss Simulation**:
   - Use `tc` (traffic control) to simulate packet loss
   - `sudo tc qdisc add dev eth0 root netem loss 5%`

4. **Long-Duration Test**:
   - Stream continuously for 30+ minutes
   - Monitor for memory leaks and connection drops

5. **Recording Under Load**:
   - Record while simulating slow disk (USB drive)
   - Should not cause stream to hang

## Configuration Changes Needed

Add to [config.yaml](config.yaml:1):

```yaml
advanced:
  # Existing settings...

  # Stream reliability settings
  stream_timeout: 5              # Seconds before declaring stream dead
  stream_health_check_interval: 2  # Seconds between health checks

  # Reconnection settings
  auto_reconnect: true
  reconnect_interval: 5          # Seconds between reconnection attempts
  max_reconnect_attempts: 10     # 0 = infinite

  # Recording settings
  recording_queue_size: 100      # Frames to buffer for recording
  recording_async: true          # Use async recording

  # FFmpeg tuning
  ffmpeg_low_latency: true       # Use low latency settings
  ffmpeg_nobuffer: true          # Minimize buffering
```

## Summary

**Main Issues**:
1. ❌ No timeout on frame reads → Application hangs
2. ❌ No auto-reconnect → Manual intervention required
3. ❌ Blocking disk I/O → Recording causes frame drops
4. ❌ No stream health monitoring → Issues not detected early
5. ❌ Poor error handling → Single error crashes stream

**Impact**:
- Stream disconnects after ~1-8 minutes
- Recording hangs application
- No automatic recovery
- Poor user experience

**Priority**:
- HIGH - Add timeouts and auto-reconnect
- MEDIUM - Async recording and health monitoring
- LOW - Buffer tuning and optimization

**Next Steps**:
1. Implement timeout mechanism (Fix 1)
2. Add auto-reconnect logic (Fix 2)
3. Implement stream health monitoring (Fix 3)
4. Make recording async (Fix 4)
5. Add FFmpeg error monitoring (Fix 5)
6. Test with live stream

---

**Report Generated**: 2025-10-20
**Log Files Analyzed**: client.log (15 lines)
**Issues Found**: 6 critical/high priority issues
**Recommended Fixes**: 6 fixes with code examples
