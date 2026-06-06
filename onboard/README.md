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
[camera thread]  --latest frame-->  [inference thread]  --tracks/alerts-->  [IO thread]
   capture.py                       detector+tracker+iff                    mavlink + gcs ws
                                                                            telemetry @ fixed 1 Hz
```

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
    config.py     # all tunables, from env/.env (nothing hardcoded)
    capture.py    # Module 1: threaded camera (picamera2 | opencv)
    detector.py   # Module 2: YOLOv8n NCNN inference            (next)
    tracker.py    # Module 3: DeepSort                          (next)
    iff.py        # Module 4: isolated friend/foe policy        (next)
    geo.py        # target pixel -> ground lat/lon projection   (next)
    mavlink_io.py # Module 5: pymavlink telemetry + commands    (next)
    gcs_client.py # Module 6/7: WS client + command dispatch    (next)
    schemas.py    # builds GCS-schema-exact messages            (next)
    pipeline.py   # wires the threads together                  (next)
    __main__.py   # entrypoint                                  (next)
  requirements.txt
  .env.example
  eqaab.service   # systemd unit                                (next)
```

## Install (on the Pi 5, Raspberry Pi OS Bookworm 64-bit)

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-venv libcap-dev

cd ~/eqaab-onboard
python3 -m venv --system-site-packages .venv   # --system-site-packages exposes picamera2
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # then edit .env: GCS_WS_URL, MAVLINK_CONNECTION, MODEL_PATH...
```

## Run

```bash
source .venv/bin/activate
python -m eqaab_edge        # full pipeline (added in a later module)
```

Build status: **Module 1 (camera capture) delivered.** Remaining modules added one at a
time after review.
