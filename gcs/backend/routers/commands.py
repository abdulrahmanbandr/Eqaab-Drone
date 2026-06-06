"""
Eqaab GCS — Command Router

REST endpoints for sending commands to the drone.
Commands are validated server-side before forwarding.
"""

import time
import logging
from fastapi import APIRouter, HTTPException

from models.schemas import (
    CommandRequest,
    CommandResponse,
    EventMessage,
)

logger = logging.getLogger("eqaab.cmd")

router = APIRouter(prefix="/api/commands", tags=["commands"])

# These will be set by main.py at startup
simulator = None
ws_manager = None


@router.post("/", response_model=CommandResponse)
async def send_command(request: CommandRequest):
    """
    Send a command to the drone.

    In production, this would forward to the drone via WebSocket.
    In simulator mode, it's handled locally.
    """
    if simulator is None:
        raise HTTPException(status_code=503, detail="Drone not connected")

    logger.info(f"Command received: {request.command} | params: {request.params}")

    # Execute command
    response = simulator.handle_command(request.command, request.params)

    # Broadcast event to all GCS clients
    if ws_manager:
        status = "OK" if response.success else "FAILED"
        event = EventMessage(
            timestamp=time.time(),
            category="command",
            message=f"[{status}] {request.command.value}: {response.message}",
        )
        await ws_manager.broadcast(event)

        # Also broadcast the ACK
        await ws_manager.broadcast(response)

    return response


@router.get("/state")
async def get_drone_state():
    """Get current drone state snapshot."""
    if simulator is None:
        raise HTTPException(status_code=503, detail="Drone not connected")

    return {
        "armed": simulator.armed,
        "flight_mode": simulator.flight_mode,
        "drone_state": simulator.drone_state,
        "battery": round(simulator.battery, 1),
        "alt": round(simulator.alt, 1),
        "lat": simulator.lat,
        "lon": simulator.lon,
        "mission_active": simulator.mission_active,
        "mission_paused": simulator.mission_paused,
        "rtl_active": simulator.rtl_active,
    }
