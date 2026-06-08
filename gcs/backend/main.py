"""
Eqaab GCS — Backend Server

Main entry point. Run with:
    python main.py

Or with uvicorn directly:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import asyncio
import json
import time
import uuid
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import config
from models.schemas import (
    InitialState,
    EventMessage,
    AlertMessage,
    ThreatLevel,
    ConnectionStatus,
)
from services.websocket_manager import ConnectionManager
from services.drone_simulator import DroneSimulator
from routers import commands, mission

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("eqaab.main")

# ──────────────────────────────────────────────
# App setup
# ──────────────────────────────────────────────

app = FastAPI(
    title="Eqaab GCS Backend",
    description="Ground Control Station backend for the Eqaab autonomous drone system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Services
# ──────────────────────────────────────────────

ws_manager = ConnectionManager()
simulator = DroneSimulator() if config.SIMULATOR_ENABLED else None

# Inject dependencies into routers
commands.simulator = simulator
commands.ws_manager = ws_manager

# Register routers
app.include_router(commands.router)
app.include_router(mission.router)

# ──────────────────────────────────────────────
# Background task: telemetry + detection loop
# ──────────────────────────────────────────────

async def telemetry_loop():
    """
    Main simulation loop.
    Runs at TELEMETRY_RATE_HZ, broadcasts telemetry and detections.
    """
    if simulator is None:
        logger.warning("Simulator disabled, telemetry loop not started")
        return

    interval = 1.0 / config.TELEMETRY_RATE_HZ
    logger.info(
        f"Telemetry loop started at {config.TELEMETRY_RATE_HZ} Hz "
        f"(interval={interval:.2f}s)"
    )

    last_time = time.time()

    while True:
        try:
            now = time.time()
            dt = now - last_time
            last_time = now

            # Update simulator state
            telemetry = simulator.update(dt)

            # Broadcast telemetry to all GCS clients
            await ws_manager.broadcast(telemetry)

            # Check for detections
            detection = simulator.maybe_generate_detection()
            if detection:
                await ws_manager.broadcast(detection)

                # Store in alert history
                alert_data = detection.model_dump()
                mission.add_alert(alert_data)

                # Generate alert for high-threat detections
                if detection.threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
                    alert = AlertMessage(
                        alert_id=str(uuid.uuid4())[:8],
                        title=f"⚠ {detection.detection_class.upper()} detected",
                        description=(
                            f"Unknown {detection.detection_class} detected with "
                            f"{detection.confidence:.0%} confidence. "
                            f"Track #{detection.track_id}"
                        ),
                        threat_level=detection.threat_level,
                        source_track_id=detection.track_id,
                        lat=detection.target_lat,
                        lon=detection.target_lon,
                    )
                    await ws_manager.broadcast(alert)

                # Log event
                event = EventMessage(
                    category="detection",
                    message=(
                        f"Detection: {detection.detection_class} "
                        f"(conf: {detection.confidence:.0%}, "
                        f"IFF: {detection.iff_status.value}, "
                        f"track #{detection.track_id})"
                    ),
                )
                await ws_manager.broadcast(event)
                mission.add_event(event.model_dump())

            await asyncio.sleep(interval)

        except asyncio.CancelledError:
            logger.info("Telemetry loop cancelled")
            break
        except Exception as e:
            logger.error(f"Telemetry loop error: {e}")
            await asyncio.sleep(1)


# ──────────────────────────────────────────────
# WebSocket endpoint
# ──────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket connection for GCS clients.

    On connect: sends initial state (home position, geofence, waypoints).
    Then receives commands and sends telemetry/detections.
    """
    await ws_manager.connect(websocket)

    try:
        # Send initial state to new client
        initial = InitialState(
            home_lat=config.HOME_LAT,
            home_lon=config.HOME_LON,
            geofence=config.GEOFENCE,
            patrol_waypoints=config.PATROL_WAYPOINTS,
            friendly_drone_ids=config.FRIENDLY_DRONE_IDS,
        )
        await ws_manager.send_to(websocket, initial)

        # Send connection event
        event = EventMessage(
            category="system",
            message=f"GCS client connected (total: {ws_manager.client_count})",
        )
        await ws_manager.broadcast(event)

        # Listen for messages from this client
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                if msg_type == "ping":
                    await ws_manager.send_to(websocket, {
                        "type": "pong",
                        "timestamp": time.time(),
                    })
                elif msg_type == "command":
                    # Commands originate at a frontend client and must reach the drone.
                    if simulator is not None:
                        # Dev/simulator mode: execute locally and broadcast the ACK.
                        from models.schemas import CommandRequest, CommandType
                        cmd = CommandRequest(
                            command=CommandType(msg.get("command")),
                            params=msg.get("params", {}),
                        )
                        response = simulator.handle_command(cmd.command, cmd.params)
                        await ws_manager.broadcast(response)
                    else:
                        # Real-drone mode: forward the command to the on-board Pi (which is
                        # just another client on this endpoint and ignores non-command types).
                        await ws_manager.broadcast(msg)
                elif msg_type in ("telemetry", "detection", "event", "alert", "command_ack"):
                    # Messages ORIGINATING from the on-board Pi (drop-in for the simulator):
                    # relay verbatim to all GCS frontend clients — the broker does not
                    # transform content. Frontend needs zero changes.
                    await ws_manager.broadcast(msg)
                    if msg_type == "detection":
                        mission.add_alert(msg)      # persist to alert/detection history
                    elif msg_type == "event":
                        mission.add_event(msg)      # persist to the event log

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from client: {data[:100]}")
            except Exception as e:
                logger.error(f"Error handling client message: {e}")

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await ws_manager.disconnect(websocket)
        event = EventMessage(
            category="system",
            message=f"GCS client disconnected (total: {ws_manager.client_count})",
        )
        await ws_manager.broadcast(event)


# ──────────────────────────────────────────────
# Startup / Shutdown
# ──────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    logger.info("=" * 50)
    logger.info("  EQAAB GCS Backend Starting")
    logger.info(f"  Simulator: {'ENABLED' if config.SIMULATOR_ENABLED else 'DISABLED'}")
    logger.info(f"  Home: ({config.HOME_LAT}, {config.HOME_LON})")
    logger.info(f"  Telemetry rate: {config.TELEMETRY_RATE_HZ} Hz")
    logger.info("=" * 50)

    # Start telemetry background task
    asyncio.create_task(telemetry_loop())


@app.on_event("shutdown")
async def shutdown():
    logger.info("Eqaab GCS Backend shutting down")


# ──────────────────────────────────────────────
# REST root
# ──────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "Eqaab GCS Backend",
        "version": "1.0.0",
        "status": "running",
        "simulator": config.SIMULATOR_ENABLED,
        "ws_endpoint": "/ws",
        "docs": "/docs",
    }


# ──────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
        log_level="info",
    )
