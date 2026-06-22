# Eqaab (عقاب) — Project Context

## Overview
Eqaab is an **intelligent autonomous aerial surveillance drone**. Its core differentiator is a
**vision-based IFF (Identify Friend or Foe)** module that classifies drones, human intruders, and
unauthorized vehicles in real time — **without radar or transponders**, using cameras only.
This is a CS graduation capstone project.

## Architecture (3-tier)
1. **Drone edge** — Raspberry Pi 5 companion computer + PX4 on a Pixhawk flight controller.
   Runs the camera, the YOLOv8n + DeepSort detection/tracking pipeline, and the IFF logic.
2. **Communication** — 4G LTE. The drone opens an **outbound WebSocket (WSS)** to a fixed public
   cloud endpoint at mission start and keeps it alive. All messages are **JSON**.
3. **Backend (GCS)** — FastAPI + WebSocket. Acts as a **message broker**: receives, persists, and
   relays — it does not transform message content. Pydantic schemas. SQLite (dev) / PostgreSQL (prod).
4. **Frontend (GCS dashboard)** — React + Leaflet.js. Dark theme with orange accents.

## Tech stack
- **Flight:** PX4 / Pixhawk. The on-board **GCS telemetry bridge uses `pymavlink` directly**
  (lightweight). Do **not** add ROS 2 / MAVROS to this bridge node. (ROS 2/MAVROS may exist
  elsewhere in the broader autonomy stack, but not in this node.)
- **AI/ML:** YOLOv8n. Use the **single unified custom model `best.pt`** with classes
  `drone=0, person=1, car=2` (one inference pass). DeepSort for tracking. Trained on Kaggle (T4),
  datasets from Roboflow.
- **Backend:** FastAPI, WebSocket, Pydantic, SQLite/PostgreSQL.
- **Frontend:** React, Leaflet.js.
- **Dev env:** macOS (MacBook Air). Use `python3` / `pip3` inside a `venv`.

## Immutable rules (these override conflicting prompts)
- **No video streaming, by design.** It halves AI inference FPS and uses ~300x more bandwidth for
  minimal benefit. Send **structured data + snapshots only**.
- **Drop-in replacement / zero frontend changes.** The real Pi WebSocket connection replaces the
  development simulator. The Pi **must emit the exact existing message schema** — never invent or
  rename fields, never add fields the frontend doesn't already read.
- **RC override is hardware-level.** On PX4, manual RC (2.4 GHz direct to Pixhawk) bypasses all
  software and always takes priority. Never write code that attempts to bypass or suppress it.
- **Single unified detection model**, not sequential separate models — merging all datasets into one
  training run solved catastrophic forgetting (the fine-tuned model was forgetting COCO classes).
- **Lightweight on the Pi 5.** Prefer NCNN/ONNX export, small input size (320/416), threaded
  capture/inference/IO, and detection every N frames with DeepSort coasting between.

## WebSocket message schema (match exactly)
Every message is JSON with a `type` field. **The authoritative field names live in
`backend/models/schemas.py`** — verify against it before sending anything.

```json
// telemetry — every 1 second
{ "type":"telemetry", "timestamp":"<ISO8601>", "drone_id":"eqaab-01",
  "latitude":21.3891, "longitude":40.1234, "altitude_m":35.2,
  "heading_deg":270, "speed_ms":4.1, "battery_pct":78,
  "flight_mode":"PATROL", "armed":true }

// alert — on a confirmed tracked target
{ "type":"alert", "timestamp":"<ISO8601>", "drone_id":"eqaab-01",
  "track_id":7, "target_class":"drone", "confidence":0.91,
  "iff_status":"UNKNOWN", "target_latitude":21.3887, "target_longitude":40.1229,
  "drone_altitude_m":35.2, "bbox":[312,198,401,267] }

// command — GCS -> drone
{ "type":"command", "timestamp":"<ISO8601>", "drone_id":"eqaab-01",
  "command":"RTH", "parameters":{} }
```
Valid `command` values: `TAKEOFF`, `LAND`, `RTH`, `PAUSE`, `RESUME`, `UPLOAD_MISSION`, `SET_GEOFENCE`.

## Project structure (backend)
```
backend/
  config.py                      # HOME_LAT/LON, waypoints, geofence, rates, flags
  main.py                        # FastAPI app, WebSocket endpoint, telemetry loop
  models/schemas.py              # Pydantic message models (SOURCE OF TRUTH for fields)
  services/websocket_manager.py  # ConnectionManager.broadcast()
  services/drone_simulator.py    # dev simulator — to be replaced by the real Pi connection
  routers/commands.py            # REST command endpoints + validation
  routers/mission.py             # mission config, alerts, events, health
```

## How to work in this project
- Make changes **step-by-step, one module at a time**, and wait for confirmation before advancing.
- State assumptions explicitly before writing code.
- Match existing conventions and the schema above; don't restructure working code without asking.
- Technical content/code is in **English**; official/registration materials may be in **Arabic**.
