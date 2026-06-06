# Eqaab GCS — Ground Control Station

Autonomous drone control system with AI-based detection, real-time telemetry, and web-based command interface.

## Project Structure

```
eqaab-gcs/
├── backend/
│   ├── main.py                    # FastAPI app — run this
│   ├── config.py                  # Settings (coordinates, rates, etc.)
│   ├── requirements.txt           # Python dependencies
│   ├── models/
│   │   └── schemas.py             # All message schemas (Pydantic)
│   ├── services/
│   │   ├── websocket_manager.py   # WebSocket connection manager
│   │   └── drone_simulator.py     # Mock drone (replace with real drone later)
│   └── routers/
│       ├── commands.py            # REST: POST /api/commands/
│       └── mission.py             # REST: GET /api/alerts, /api/mission/config
└── frontend/
    ├── package.json
    ├── vite.config.js             # Dev server + proxy to backend
    ├── index.html
    └── src/
        ├── main.jsx               # Entry point
        ├── App.jsx                # Layout grid
        ├── styles/theme.css       # Dark theme + orange accents
        ├── context/DroneContext.jsx # Central WebSocket state
        ├── hooks/useWebSocket.js  # WS connection + heartbeat
        ├── services/api.js        # REST client
        └── components/
            ├── TopBar.jsx         # Connection, mode, armed state
            ├── MapPanel.jsx       # Leaflet map + overlays
            ├── TelemetryPanel.jsx # Metric cards
            ├── DetectionPanel.jsx # AI detection feed
            ├── CommandPanel.jsx   # Flight commands
            └── EventLog.jsx       # System event log
```

## Quick Start — Full System

### Frontend (React + Leaflet.js)

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:3000`. The Vite proxy forwards `/api` and `/ws` to the backend at port 8000.

### Backend (FastAPI)

### 1. Install Python dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Run the server

```bash
python main.py
```

The server starts at `http://localhost:8000`.

### 3. Verify it works

- Open `http://localhost:8000` — should return service info JSON
- Open `http://localhost:8000/docs` — interactive API documentation
- WebSocket endpoint: `ws://localhost:8000/ws`

## API Endpoints

### REST

| Method | Endpoint               | Description                        |
|--------|------------------------|------------------------------------|
| GET    | `/`                    | Service info                       |
| GET    | `/docs`                | Swagger API docs                   |
| POST   | `/api/commands/`       | Send command to drone              |
| GET    | `/api/commands/state`  | Current drone state                |
| GET    | `/api/alerts`          | Recent detection alerts            |
| GET    | `/api/events`          | Recent event log                   |
| GET    | `/api/mission/config`  | Mission waypoints, geofence, home  |
| GET    | `/api/health`          | Health check                       |

### WebSocket (`/ws`)

On connect, the server sends `initial_state` with home position, geofence, and waypoints.

Then it streams these message types:

| Type               | Direction       | Description                      |
|--------------------|-----------------|----------------------------------|
| `telemetry`        | server → client | Position, battery, speed (2 Hz)  |
| `detection`        | server → client | AI detection with IFF + GPS      |
| `alert`            | server → client | High-threat alert                |
| `event`            | server → client | System event log entry           |
| `command_ack`      | server → client | Command result                   |
| `initial_state`    | server → client | Config on first connect          |
| `ping` / `pong`    | bidirectional   | Connection heartbeat             |
| `command`          | client → server | Inline command (alternative to REST) |

### Command Examples

```bash
# Arm the drone
curl -X POST http://localhost:8000/api/commands/ \
  -H "Content-Type: application/json" \
  -d '{"command": "arm", "params": {}}'

# Takeoff to 15 meters
curl -X POST http://localhost:8000/api/commands/ \
  -H "Content-Type: application/json" \
  -d '{"command": "takeoff", "params": {"altitude": 15.0}}'

# Start patrol mission
curl -X POST http://localhost:8000/api/commands/ \
  -H "Content-Type: application/json" \
  -d '{"command": "start_mission", "params": {}}'

# Return to launch
curl -X POST http://localhost:8000/api/commands/ \
  -H "Content-Type: application/json" \
  -d '{"command": "rtl", "params": {}}'

# Go to specific GPS coordinate
curl -X POST http://localhost:8000/api/commands/ \
  -H "Content-Type: application/json" \
  -d '{"command": "goto", "params": {"lat": 21.488, "lon": 39.195, "alt": 50}}'
```

## Simulator Mode

When `SIMULATOR_ENABLED = True` in `config.py` (default), the backend runs a drone simulator that:

- Generates realistic telemetry at 2 Hz
- Simulates flying between patrol waypoints near Jeddah
- Battery drains over ~30 minutes of flight
- Random detections (person, car, drone) with varying confidence
- IFF classification for drone detections (30% friendly, 70% unknown)
- Responds to all commands (arm, takeoff, RTL, goto, etc.)
- Auto-RTL when battery drops below 20%

## Connecting Real Drone (Production)

Replace the simulator with a WebSocket client on the Raspberry Pi 5:

1. Set `SIMULATOR_ENABLED = False` in `config.py`
2. The Pi's `comms_node` connects to `ws://server:8000/ws`
3. Pi sends telemetry/detection JSON messages
4. Pi receives command JSON messages
5. The frontend code stays exactly the same
