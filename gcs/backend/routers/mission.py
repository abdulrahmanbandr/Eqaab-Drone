"""
Eqaab GCS — Mission & Alerts Router

REST endpoints for mission configuration and alert history.
"""

import time
from fastapi import APIRouter

import config

router = APIRouter(prefix="/api", tags=["mission"])

# In-memory stores (replace with PostgreSQL in production)
alert_history: list[dict] = []
event_log: list[dict] = []


def add_alert(alert: dict):
    """Store an alert in history."""
    alert_history.append(alert)
    # Keep last 200 alerts
    if len(alert_history) > 200:
        alert_history.pop(0)


def add_event(event: dict):
    """Store an event in log."""
    event_log.append(event)
    if len(event_log) > 500:
        event_log.pop(0)


@router.get("/alerts")
async def get_alerts(limit: int = 50):
    """Get recent alerts."""
    return {"alerts": alert_history[-limit:]}


@router.get("/events")
async def get_events(limit: int = 100):
    """Get recent events."""
    return {"events": event_log[-limit:]}


@router.get("/mission/config")
async def get_mission_config():
    """Get current mission configuration."""
    return {
        "home": {
            "lat": config.HOME_LAT,
            "lon": config.HOME_LON,
            "alt": config.HOME_ALT,
        },
        "waypoints": config.PATROL_WAYPOINTS,
        "geofence": config.GEOFENCE,
        "friendly_drone_ids": config.FRIENDLY_DRONE_IDS,
    }


@router.get("/health")
async def health_check():
    """System health check."""
    return {
        "status": "ok",
        "timestamp": time.time(),
        "simulator_mode": config.SIMULATOR_ENABLED,
    }
