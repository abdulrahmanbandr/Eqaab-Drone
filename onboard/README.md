# Eqaab (عقاب) — On-Board Edge Node (Raspberry Pi 5)

Lightweight companion-computer software for the Eqaab autonomous surveillance drone.
Runs the vision-based **IFF** pipeline, bridges **PX4** telemetry via `pymavlink`, and
keeps an outbound **WebSocket (WSS)** to the Ground Control Station — emitting the
**exact** message schema defined in `eqaab-gcs/backend/models/schemas.py` (drop-in
replacement for the dev simulator; zero frontend changes).

> **No video streaming, by design.** Structured data + (optional) snapshots only.
> **RC override is hardware-level on PX4** and always wins — this software never bypasses it.

## Architecture (threads, nothing blocks anything)

```
[camera thread]  --latest frame-->  [inference thread]  --detections-->  [ws I/O thread]
   capture.py                       detect → track → IFF                 gcs_client.py
                                                                          telemetry @ fixed 1 Hz
        [mavlink thread] mavlink_bridge.py  <-- telemetry / commands -->  PX4 (Pixhawk)
```

Data flow:
- MAVLink telemetry → WS client's **1 Hz** timer → `telemetry` message.
- Confirmed track → `build_detection()` (+ live telemetry & geo-projection) → `detection` message.
- GCS `command` → WS client → `CommandHandler` → MAVLink → PX4 (with `event` feedback).

## Performance budget (Pi 5, to validate on-device)

| Item            | Target |
|-----------------|--------|
| Model           | YOLOv8n exported to **NCNN** (preferred) / ONNX — never raw `.pt` if avoidable |
| Input size      | **320** (or 416), never 640 |
| Detection rate  | every **3rd** frame; DeepSort coasts between |
| Capture FPS     | ~15–25 |
| Inference rate  | ~8–12/s |
| CPU             | ~1.5–2 of 4 cores |
| RAM             | ~400–600 MB |
| Telemetry       | fixed **1 Hz**, independent of vision FPS |

## Layout

```
eqaab-onboard/
  eqaab_edge/
    config.py          # all tunables, from env/.env (nothing hardcoded)
    capture.py         # Module 1: threaded camera (picamera2 | opencv)
    detect.py          # Module 2: unified YOLOv8n, one inference pass (NCNN/ONNX/.pt)
    export_ncnn.py     #           one-shot best.pt -> NCNN export helper
    track.py           # Module 3: DeepSort, stable track_ids, Kalman coasting
    iff.py             # Module 4: single isolated friend/foe policy
    pipeline.py        # Module 4: capture->detect->track->IFF inference thread
    mavlink_bridge.py  # Module 5: pymavlink telemetry + command senders
    geo.py             #           target pixel -> ground lat/lon projection
    messages.py        # Module 6: schema-exact telemetry/detection builders
    gcs_client.py      # Module 6: outbound WSS client (1Hz telem, detections, reconnect)
    commands.py        # Module 7: GCS command -> PX4 dispatch (+ RC-override notes)
    app.py             # Module 8: orchestrator (wires all threads, graceful shutdown)
    __main__.py        # entrypoint: python -m eqaab_edge
  requirements.txt
  .env.example
  eqaab.service        # systemd unit (auto-start on boot)
```

## Install (on the Pi 5, Raspberry Pi OS Bookworm 64-bit)

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-venv libcap-dev

cd ~/eqaab-onboard
python3 -m venv --system-site-packages .venv   # --system-site-packages exposes picamera2
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # then edit: GCS_WS_URL, MAVLINK_CONNECTION, MODEL_PATH...
```

## Model: export to NCNN (do this once)

NCNN is the fastest YOLOv8n backend on a Pi 5. Export on your dev machine (or the Pi), then
point `MODEL_PATH` at the resulting directory.

```bash
# produces best_ncnn_model/ next to best.pt
python -m eqaab_edge.export_ncnn path/to/best.pt --imgsz 320
# .env:  MODEL_PATH=models/best_ncnn_model
```

## Run

```bash
source .venv/bin/activate

# Vision only (no MAVLink / no GCS) — validate camera + model + tracker on-device:
python -m eqaab_edge.pipeline

# Full edge node (vision + MAVLink + GCS WebSocket + commands):
python -m eqaab_edge
```

## Auto-start on boot (systemd)

```bash
sudo cp eqaab.service /etc/systemd/system/eqaab.service
# edit User/paths inside if not cloned to /home/pi/eqaab-onboard
sudo systemctl daemon-reload
sudo systemctl enable --now eqaab.service
journalctl -u eqaab -f          # follow logs
```

## Configuration

Every operational value lives in `.env` (see `.env.example`) — nothing is hardcoded. Key knobs:

| Variable | Purpose |
|----------|---------|
| `GCS_WS_URL` / `GCS_AUTH_TOKEN` | Outbound WSS endpoint + optional bearer auth |
| `MAVLINK_CONNECTION` / `MAVLINK_BAUD` | `/dev/ttyACM0`, `/dev/serial0`, or `udp:127.0.0.1:14540` |
| `MODEL_PATH` / `IMG_SIZE` / `DETECT_EVERY_N` | Detector backend, input size, detect cadence |
| `CONF_THRESHOLD` / `IOU_THRESHOLD` | Detector thresholds |
| `TRACK_*` | DeepSort tuning (age, init, embedder) |
| `CAM_HFOV_DEG` / `CAM_VFOV_DEG` / `CAM_MOUNT_PITCH_DOWN_DEG` | Camera geometry for target geo-projection |
| `FRIENDLY_DRONE_IDS` / `IFF_HOSTILE_MIN_CONF` | IFF policy inputs |

## GCS backend note (one small change required)

The Pi emits `schemas.py`-exact `telemetry` / `detection` / `event` messages. The current
GCS backend `/ws` endpoint still runs an in-process simulator and only reads `ping`/`command`
from clients. To let the real Pi drive the dashboard, the backend must (a) set
`SIMULATOR_ENABLED = False`, and (b) rebroadcast inbound drone messages to frontend clients.
A ready-made drop-in guide lives at `gcs/backend/DRONE_INGEST.md` in this repo. **The
frontend needs no changes.**

---

Build status: **complete** — Modules 1–8 delivered (camera, detector, tracker, IFF,
pipeline, MAVLink bridge + geo, message builder + WS client, commands, orchestrator + systemd).
