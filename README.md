<div align="center">

# Eqaab (عقاب) — Autonomous Aerial Surveillance Drone

**Vision-based IFF (Identify Friend or Foe) — no radar, no transponders, cameras only.**

CE graduation capstone project · Open source under the MIT License

</div>

---

Eqaab is an intelligent autonomous surveillance drone whose core differentiator is a
real-time, **vision-only IFF** module that classifies drones, human intruders, and
unauthorized vehicles — without radar or transponders. This repository contains the full
three-tier system.

## Architecture

```
   ┌────────────────────┐        4G LTE / WSS        ┌────────────────────┐
   │   Drone edge        │  ───── outbound JSON ────► │   GCS backend       │
   │  Raspberry Pi 5     │  ◄──── commands ─────────  │  FastAPI + WS       │
   │  + PX4 / Pixhawk    │                            │  (message broker)   │
   │  YOLOv8n + DeepSort │                            └─────────┬──────────┘
   │  + IFF + pymavlink  │                                      │
   └────────────────────┘                            ┌─────────▼──────────┐
                                                      │   GCS dashboard     │
                                                      │  React + Leaflet    │
                                                      └────────────────────┘
```

## Repository layout

| Path | What it is | Stack |
|------|-----------|-------|
| [`onboard/`](onboard/) | On-board edge node for the Raspberry Pi 5 companion computer: camera capture, YOLOv8n+DeepSort detection/tracking, IFF policy, `pymavlink` telemetry bridge, and the outbound WebSocket client to the GCS. | Python, picamera2, Ultralytics/NCNN, DeepSort, pymavlink |
| [`gcs/`](gcs/) | Ground Control Station: a WebSocket message broker that persists and relays drone telemetry/detections, plus the operator dashboard. | FastAPI + WebSocket + Pydantic (backend), React + Leaflet.js (frontend) |
| [`landing/`](landing/) | Public project landing page / team site. | Next.js + TypeScript |

## Key design principles

- **No video streaming, by design** — structured data + snapshots only (saves bandwidth and inference FPS).
- **Lightweight on the Pi 5** — NCNN/ONNX export, small input size (320/416), threaded capture/inference/IO, detection every N frames with DeepSort coasting between.
- **`pymavlink` directly** — no ROS 2 / MAVROS on the edge node.
- **RC override is hardware-level on PX4** and always takes priority — no software here ever bypasses it.
- **Single source of truth for the wire protocol** — `gcs/backend/models/schemas.py` defines every JSON message; the edge node matches it exactly.

## Quick start

Each component has its own README with full setup instructions:

- **Edge node (Pi 5):** [`onboard/README.md`](onboard/README.md)
- **GCS backend + frontend:** [`gcs/README.md`](gcs/README.md)
- **Landing page:** [`landing/README.md`](landing/README.md)

## License

[MIT](LICENSE) © 2026 Eqaab Team.
