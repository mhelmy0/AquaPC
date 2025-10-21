# Quick Start Guide

Get up and running with the RTP Video Streaming Client in 5 minutes!

## Prerequisites Checklist

- [ ] Python 3.8+ installed
- [ ] FFmpeg installed and in PATH
- [ ] Raspberry Pi server streaming on 192.168.100.41:5000
- [ ] Network connectivity to Raspberry Pi

## Installation (3 steps)

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install FFmpeg

**Windows**: Download from https://ffmpeg.org/download.html and add to PATH
**Linux**: `sudo apt install ffmpeg`
**macOS**: `brew install ffmpeg`

Verify: `ffmpeg -version`

### 3. Update Configuration (Optional)

Edit `config.yaml` if your Raspberry Pi has a different IP:

```yaml
stream:
  source_ip: "YOUR_RASPBERRY_PI_IP"  # Change this if needed
  rtp_port: 5000
```

## Running the Application

```bash
python main.py
```

That's it! Click **Connect** to start viewing the stream.

## Quick Test

Before running the client, test the stream with FFmpeg:

```bash
ffplay -protocol_whitelist file,rtp,udp rtp://192.168.100.41:5000
```

If this works, the client will work too!

## Common Issues

### "FFmpeg not found"
- Make sure FFmpeg is installed: `ffmpeg -version`
- Add FFmpeg to system PATH

### "Connection failed"
- Verify Raspberry Pi is streaming
- Check IP address is correct (192.168.100.41)
- Ping the Raspberry Pi: `ping 192.168.100.41`

### "No video displayed"
- Check server is actively sending video
- Try restarting both client and server
- Check firewall isn't blocking port 5000

## Basic Usage

1. **Start**: `python main.py`
2. **Connect**: Click "Connect" button
3. **Record**: Click "Start Recording" (while connected)
4. **Snapshot**: Click "Take Snapshot" (while connected)
5. **Stop**: Click "Disconnect" or close window

## Output Files

- **Recordings**: Saved to `./recordings/` as MP4 files
- **Snapshots**: Saved to `./snapshots/` as JPG files
- **Logs**: Check `client.log` for troubleshooting

## Next Steps

- Read [README.md](README.md) for full documentation
- Customize settings in [config.yaml](config.yaml)
- Check troubleshooting section if issues occur

## Server Setup (Raspberry Pi)

If you need to set up the server, use this FFmpeg command:

```bash
ffmpeg -re -f h264 -i - -c:v copy -an -f rtp -rtpflags latm -pkt_size 1200 -sdp_file /tmp/stream.sdp rtp://192.168.100.41:5000
```

Replace `192.168.100.41` with your client PC's IP address.

---

Need help? Check the [Troubleshooting section in README.md](README.md#troubleshooting)
