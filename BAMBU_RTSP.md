# RTSP Substream Guide for Bambu Labs 3D Printer Camera

[![go2rtc](https://img.shields.io/badge/go2rtc-v1.9.x-blue.svg)](https://github.com/AlexxIT/go2rtc) [![Debian](https://img.shields.io/badge/Debian-Trixie-orange.svg)](https://www.debian.org/releases/trixie/)

This guide shows you how to install and configure [go2rtc](https://github.com/AlexxIT/go2rtc) on **Debian Trixie** (Debian 13) to create a low-bandwidth RTSP substream from your Bambu Labs 3D printer's camera (e.g., X1C, P1P). The substream is transcoded to H.264 at 360p/15fps for efficient mobile or remote viewing, perfect for integration with Home Assistant, Frigate, or VLC.

go2rtc acts as a media server, pulling the printer's raw RTSP feed and generating an optimized version on-demand. This reduces bandwidth and CPU usage compared to the full 1080p stream.

> **Note**: Tested as of December 2025.

## Prerequisites

- **Bambu Labs Printer Setup**:
  - Enable **LAN Mode** in Bambu Studio (Device > Camera Settings).
  - Note your printer's **local IP address** (e.g., `192.168.1.100` from router or app).
  - Retrieve the **Access Code** (in Bambu Studio under Device > Camera > Access Code).
- **Hardware**: Raspberry Pi ARM64 or similar machine. GPU optional for hardware acceleration.
- **Network**: Printer and Debian machine connecivity allowing ports 322 (printer RTSP) and 8554 (go2rtc RTSP).

Update your Debian system:
```bash
sudo apt update && sudo apt upgrade -y
```

## Step 1: Install go2rtc from Source

### Install Dependencies
```bash
sudo apt install -y golang-go git ffmpeg
```

### Clone and Build
```bash
git clone https://github.com/AlexxIT/go2rtc.git
cd go2rtc
go mod download  # Fetch dependencies if needed
go build -o go2rtc main.go
```

### Install Binary
```bash
chmod +x go2rtc
sudo mv go2rtc /usr/local/bin/
```

### Verify
```bash
go2rtc version  # Should show v1.9.x or later
```

## Step 2: Set Up as a Systemd Service

Run go2rtc as a non-root service for security.

### Create System User and Group
```bash
sudo groupadd --system go2rtc
sudo useradd --system --no-create-home -g go2rtc go2rtc
```

### Create Service File
```bash
sudo nano /etc/systemd/system/go2rtc.service
```

Add the following:
```ini
[Unit]
Description=go2rtc media server
After=network.target

[Service]
Type=simple
User=go2rtc
Group=go2rtc
ExecStart=/usr/local/bin/go2rtc -c /etc/go2rtc/go2rtc.yaml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Enable and Start
```bash
sudo systemctl daemon-reload
sudo systemctl enable go2rtc
sudo systemctl start go2rtc
sudo systemctl status go2rtc  # Check for errors
```

### Create Config Directory
```bash
sudo mkdir -p /etc/go2rtc
sudo chown -R go2rtc:go2rtc /etc/go2rtc
```

## Step 3: Configure Streams

Edit the config file:
```bash
sudo nano /etc/go2rtc/go2rtc.yaml
```

Replace with this YAML (update `<access_code>` and `<printer_ip>`):
```yaml
# go2rtc configuration for Bambu Labs printer streams
# See https://github.com/AlexxIT/go2rtc/wiki/Configuration for more options

streams:
  bambu_main:
    # Bambu printer's main RTSP stream (encrypted rtsps)
    - rtsps://bblp:<access_code>@<printer_ip>:322/streaming/live/1

  # Transcoded substream for mobile/low-bandwidth viewing
  bambu_low:
    - ffmpeg:bambu_main#video=h264#width=-2#height=360#fps=15#crf=30

# Optional: RTSP server settings (default port 8554)
rtsp:
  listen: ":8554"
```

- **bambu_main**: Raw feed from printer (H.265, ~1080p, 30fps).
- **bambu_low**: Transcoded to H.264 (browser-friendly), 360p at 15fps, CRF=30 (balanced quality/compression).
  - `width=-2`: Auto-scale width to preserve aspect ratio.
  - Add `#hardware=vaapi` (Intel) or `#hardware=nvidia` for GPU acceleration.

Save, then restart:
```bash
sudo systemctl restart go2rtc
```

Validate YAML:
```bash
go2rtc -c /etc/go2rtc/go2rtc.yaml check
```

## Step 4: Test the Streams

### Web UI
- Open `http://<debian-ip>:1984` in a browser.
- Click `bambu_main` or `bambu_low` for live preview (WebRTC/MSE).

### VLC
Install: `sudo apt install vlc`
- Open Network Stream:
  - Main: `rtsp://<debian-ip>:8554/bambu_main`
  - Substream: `rtsp://<debian-ip>:8554/bambu_low`
