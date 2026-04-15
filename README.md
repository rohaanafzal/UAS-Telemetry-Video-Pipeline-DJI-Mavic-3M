# UAS Telemetry & Video Pipeline — DJI Mavic 3M

> Real-time GNSS telemetry extraction, RTMP video streaming, and autonomous mission event signaling for precision UAV operations.

---

## Overview

This system implements a multi-channel data pipeline for the DJI Mavic 3M multispectral UAV platform. It decouples live video delivery, GNSS telemetry forwarding, and mission event detection into three independent, fault-tolerant pipelines — enabling synchronized ground station awareness without interfering with active waypoint missions.

Designed for precision agriculture, infrastructure inspection, and research-grade UAV deployments.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AIRBORNE SEGMENT                         │
│                                                             │
│   ┌──────────────────┐         ┌───────────────────────┐   │
│   │  DJI Mavic 3M    │◄───────►│   RC Pro Controller   │   │
│   │  (Aircraft)      │  RC Link│   (Ground Operator)   │   │
│   │  - SD Recording  │         │   - DJI Mobile SDK    │   │
│   │  - .SRT Telemetry│         │   - GPS Extractor     │   │
│   │  - GNSS @ 10Hz   │         │   - RTMP Streamer     │   │
│   └──────────────────┘         └───────────┬───────────┘   │
└───────────────────────────────────────────-│───────────────┘
                                             │ WiFi (RS2 Hotspot)
                              ┌──────────────▼──────────────┐
                              │       LOCAL NETWORK         │
                              │   192.168.42.0/24           │
                              │   (Emlid RS2+ Hotspot)      │
                              └──────┬───────────┬──────────┘
                                     │           │
                          ┌──────────▼──┐   ┌────▼──────────┐
                          │  Mac (GCS)  │   │    Jetson     │
                          │ .238        │   │   .107        │
                          │ MediaMTX    │   │  UDP Receiver │
                          │ OBS Studio  │   │  Event Logger │
                          │ Row Notifier│   │  ~/Rohaan-    │
                          └─────────────┘   │  Testing-     │
                                            │  Signal/      │
                                            └───────────────┘
```

---

## Data Flow Pipelines

### 1. Video Pipeline (RTMP)
```
Mavic 3M Camera
    └── RC Pro (DJI Pilot 2 → Live Stream → Custom RTMP)
            └── rtmp://192.168.42.238:1935/live
                    └── MediaMTX (RTMP ingest server)
                            └── OBS Studio (monitor + record)
                                    └── /Users/<user>/Movies/*.mov
```

### 2. GNSS Telemetry Pipeline (UDP)
```
FlightControllerKey.KeyAircraftLocation3D
    └── DJI Mobile SDK (RC Pro Android App)
            └── TelemetrySender.kt (Coroutine, 1 Hz)
                    └── UDP → Mac/Jetson :5005
                            └── Python socket receiver
                                    └── CSV / JSONL log
```

### 3. Mission Event Pipeline (UDP)
```
OBS stops recording
    └── New .mov file created in ~/Movies/
            └── mac_row_notifier.py (inotify-style polling, 2s interval)
                    └── UDP → Jetson :7000
                            └── jetson_receiver.py
                                    └── ~/Rohaan-Testing-Signal/log_YYYYMMDD.txt
```

---

## Component Breakdown

| Component | Host | Language | Role |
|---|---|---|---|
| `TelemetrySender.kt` | RC Pro | Kotlin | Extracts GPS from DJI SDK, forwards via UDP |
| `DJIAircraftMainActivity.kt` | RC Pro | Kotlin | App entry point, initializes telemetry sender |
| `MediaMTX` | Mac | Go binary | RTMP ingest + relay server |
| `OBS Studio` | Mac | C++ | Video monitoring, recording to disk |
| `mac_row_notifier.py` | Mac | Python 3 | Watches OBS output folder, fires row-complete events |
| `jetson_receiver.py` | Jetson | Python 3 | UDP listener, persists mission events to disk |

---

## Network Configuration

| Device | IP Address | Subnet |
|---|---|---|
| Mac (Ground Station) | `192.168.42.238` | RS2 Hotspot |
| Jetson (Edge Compute) | `192.168.42.107` | RS2 Hotspot |
| RC Pro (Controller) | `192.168.42.x` | RS2 Hotspot |
| Emlid RS2+ | `192.168.42.1` | Gateway / Hotspot AP |

### Ports

| Service | Protocol | Port | Direction |
|---|---|---|---|
| RTMP ingest | TCP | `1935` | RC Pro → Mac |
| GPS telemetry | UDP | `5005` | RC Pro → Mac/Jetson |
| Row event signals | UDP | `7000` | Mac → Jetson |

---

## Setup Instructions

### Prerequisites

- macOS 13+ with Homebrew
- Jetson running Ubuntu 20.04+
- Android Studio (for RC Pro app build)
- DJI Mobile SDK v5 developer account + API key
- Emlid RS2+ with hotspot enabled

---

### 1. Ground Station (Mac)

**Install dependencies:**
```bash
brew install ffmpeg mediamtx obs
```

**Configure MediaMTX** (`~/mediamtx.yml`):
```yaml
paths:
  live:
    source: publisher
```

**Start MediaMTX:**
```bash
mediamtx ~/mediamtx.yml
```

**Start row notifier:**
```bash
python3 mac_row_notifier.py
```

**OBS Configuration:**
- Sources → Media Source → `rtmp://192.168.42.238:1935/live`
- Output → Recording Path → `/Users/<user>/Movies`
- Format: `.mov` or `.mp4`

---

### 2. Jetson (Edge Node)

**Transfer receiver script:**
```bash
scp jetson_receiver.py bsen@192.168.42.107:~/
```

**Start receiver:**
```bash
python3 ~/jetson_receiver.py
```

Logs are saved to:
```
~/Rohaan-Testing-Signal/log_YYYYMMDD.txt
```

---

### 3. RC Pro (Android App)

**Build and deploy via Android Studio:**
```
Project: Mobile-SDK-Android-V5/SampleCode-V5/android-sdk-v5-as
Module:  android-sdk-v5-sample
```

**Set API key** in `gradle.properties`:
```
AIRCRAFT_API_KEY = <your_dji_api_key>
```

**Set target IPs** in `TelemetrySender.kt`:
```kotlin
private const val MAC_IP = "192.168.42.238"
private const val UDP_PORT = 5005
```

**DJI Pilot 2 RTMP config:**
```
Settings → Live Stream → Custom RTMP
URL: rtmp://192.168.42.238:1935/live
Resolution: 720P / 30FPS
```

---

## Configuration Reference

```
# TelemetrySender.kt
MAC_IP      = 192.168.42.238
UDP_PORT    = 5005
POLL_RATE   = 1000ms (1 Hz)

# mac_row_notifier.py
OBS_FOLDER      = /Users/<user>/Movies
JETSON_IP       = 192.168.42.107
JETSON_PORT     = 7000
CHECK_INTERVAL  = 2s

# jetson_receiver.py
LISTEN_PORT = 7000
SAVE_FOLDER = ~/Rohaan-Testing-Signal/
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Waypoint mission crashes on launch | SDK callback blocking mission thread | Move `TelemetrySender.start()` to background coroutine; remove `startLiveStream()` |
| RTMP stream not received by OBS | Wrong IP in Pilot 2 or MediaMTX path unconfigured | Set URL to `rtmp://<mac_ip>:1935/live`; verify `paths.live` in `mediamtx.yml` |
| UDP packets sent but Jetson not receiving | Devices on different subnets | Confirm both devices on same AP (`192.168.42.x`); check with `ping` |
| GPS reads `0.0, 0.0` | Drone not connected or SDK not registered | Verify API key matches package name in DJI developer portal |
| Row notifier fires on existing files | Script launched after recordings already exist | Expected — script snapshots existing files on start, only alerts on new ones |
| `jetson_receiver.py` log file empty | File handle buffering | Fixed — script opens/closes file per message (no buffering) |
| SCP connection timeout | Wrong IP or SSH not enabled on Jetson | Enable SSH: `sudo systemctl enable ssh && sudo systemctl start ssh` |

---

## Known Constraints

- **Single app at a time on RC Pro** — DJI Pilot 2 and the custom SDK app cannot run simultaneously. GPS extraction requires the SDK app; waypoint missions require Pilot 2. Use post-flight `.SRT` parsing for GPS-video correlation when running Pilot 2.
- **RTMP stream quality** — Limited by hotspot bandwidth. 720P/30FPS/1.5Mbps is the practical ceiling over RS2 hotspot. Full-quality footage is available on the drone's SD card.
- **GPS rate** — SDK telemetry forwarded at 1 Hz. DJI's internal GNSS runs at up to 10 Hz; higher rates are achievable with SDK key subscription listeners.

---

## Future Improvements

- [ ] Replace polling-based row detection with `watchdog` FSEvents listener (zero-latency)
- [ ] Integrate Emlid RS2+ NMEA stream for RTK-corrected coordinates alongside SDK GPS
- [ ] Post-flight `.SRT` parser to correlate SD card video segments with waypoint boundaries
- [ ] WebSocket dashboard for real-time telemetry visualization on ground station
- [ ] Automatic `.KMZ` ingestion to pre-load waypoint coordinates for segment labeling
- [ ] Docker container for Jetson receiver with systemd auto-start

---

## Use Cases

- **Precision Agriculture** — Row-by-row multispectral capture with per-row video and GPS archiving
- **Infrastructure Inspection** — Segment-tagged video of transmission lines, pipelines, or bridges
- **Research Deployments** — Time-synced telemetry + video for UAV flight dynamics studies
- **Ground Truth Collection** — RTK-grade GPS correlation with camera frames for ML dataset labeling

---

## System Requirements

| Component | Minimum |
|---|---|
| DJI Mavic 3M firmware | v07.01.10.06+ |
| RC Pro firmware | v03.00.00.09+ |
| Android (RC Pro) | API 24+ |
| macOS | Ventura 13+ |
| Jetson | JetPack 5.x, Ubuntu 20.04 |
| Python | 3.10+ |
| FFmpeg | 6.0+ |
| MediaMTX | v1.x |

---

## License

MIT License. See `LICENSE` for details.

---

*Built for the Smart Horticultural Systems Lab — Auburn University Biosystems Engineering*
