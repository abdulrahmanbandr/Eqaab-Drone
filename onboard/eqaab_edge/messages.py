"""
Module 6 (mapping) — Wire message builders.

The ONLY place neutral internal state is mapped onto the GCS wire schema. Field names,
types and value casing here must match `backend/models/schemas.py` EXACTLY — that file is
the source of truth, so the existing frontend needs zero changes (drop-in replacement).

Two outbound message kinds the Pi produces:
  * "telemetry"  — TelemetryMessage,  sent at 1 Hz.
  * "detection"  — DetectionMessage,  sent once per confirmed track. (The backend itself
                   derives the operator-facing AlertMessage from a detection; the Pi does
                   NOT send "alert".)

Schema facts pinned from schemas.py (do not "fix" these to the prompt's example):
  * timestamp is an epoch FLOAT (time.time()), not an ISO string.
  * telemetry fields are lat/lon/alt/heading/speed/battery (not latitude/altitude_m/...).
  * detection_class (not target_class); bbox is an OBJECT {x1,y1,x2,y2} (not an array).
  * iff_status is lowercase ("friendly"/"unknown"/"hostile"); threat_level is UPPERCASE.
  * there is no drone_id field on the wire — DRONE_ID stays in logs only.
"""

from __future__ import annotations

import time
from typing import Optional

from .config import Config
from .geo import project_target, resolve_camera_orientation
from .mavlink_bridge import TelemetryState
from .pipeline import VisionAlert

# IFF status → threat level. The backend raises an operator AlertMessage only for
# HIGH/CRITICAL, so a confident hostile escalates while unknown/friendly stay calmer.
_THREAT_BY_IFF = {
    "hostile": "HIGH",
    "unknown": "MEDIUM",
    "friendly": "LOW",
}


def derive_drone_state(state: TelemetryState) -> str:
    """Best-effort DroneState (schemas.py) from armed + flight mode + altitude."""
    if not state.armed:
        return "IDLE"
    mode = state.flight_mode
    if mode == "TAKEOFF":
        return "TAKING_OFF"
    if mode == "LAND":
        return "LANDING"
    if mode == "RTL":
        return "RETURNING"
    if state.alt_rel_m < 0.5:
        return "ARMED"
    return "FLYING"


def build_telemetry(state: TelemetryState, latency_ms: int = 0) -> dict:
    """Map TelemetryState → a TelemetryMessage dict (1 Hz)."""
    return {
        "type": "telemetry",
        "timestamp": time.time(),
        # Position (lat/lon default to 0.0 until a GPS fix; gps_fix signals validity).
        "lat": state.lat if state.lat is not None else 0.0,
        "lon": state.lon if state.lon is not None else 0.0,
        "alt": round(state.alt_rel_m, 2),
        "heading": round(state.heading_deg, 1),
        # Motion
        "speed": round(state.ground_speed_ms, 2),
        "vertical_speed": round(state.vertical_speed_ms, 2),
        # Power
        "battery": round(state.battery_pct, 1),
        "voltage": round(state.voltage_v, 2),
        # GPS
        "gps_fix": int(state.gps_fix),
        "satellites": int(state.satellites),
        # State
        "armed": bool(state.armed),
        "flight_mode": state.flight_mode,
        "drone_state": derive_drone_state(state),
        # Link
        "signal_latency_ms": int(latency_ms),
    }


def build_detection(alert: VisionAlert, state: TelemetryState, cfg: Config) -> dict:
    """Map a confirmed VisionAlert + live telemetry → a DetectionMessage dict.

    Geo-projects the bbox to target_lat/target_lon when a position + altitude are known;
    leaves them null otherwise (the schema allows Optional).
    """
    target_lat: Optional[float] = None
    target_lon: Optional[float] = None
    if state.lat is not None and state.lon is not None and state.alt_rel_m > 0.0:
        azimuth, depression = resolve_camera_orientation(
            state.heading_deg, cfg.geo,
            gimbal_depression_deg=state.gimbal_depression_deg,
            gimbal_yaw_deg=state.gimbal_yaw_deg,
        )
        projected = project_target(
            alert.bbox, alert.frame_w, alert.frame_h,
            state.lat, state.lon, state.alt_rel_m,
            cam_azimuth_deg=azimuth, cam_depression_deg=depression,
            hfov_deg=cfg.geo.hfov_deg, vfov_deg=cfg.geo.vfov_deg,
        )
        if projected is not None:
            target_lat = round(projected[0], 7)
            target_lon = round(projected[1], 7)

    x1, y1, x2, y2 = alert.bbox
    # iff_id is only meaningful for a verified friendly (none on the vision-only path).
    iff_id = cfg.iff.friendly_drone_ids[0] if alert.iff_status == "friendly" and cfg.iff.friendly_drone_ids else None

    return {
        "type": "detection",
        "timestamp": time.time(),
        "detection_class": alert.class_name,
        "confidence": round(alert.confidence, 3),
        "track_id": int(alert.track_id),
        "bbox": {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)},
        "model_source": "yolov8n",
        "target_lat": target_lat,
        "target_lon": target_lon,
        "iff_status": alert.iff_status,
        "iff_id": iff_id,
        "threat_level": _THREAT_BY_IFF.get(alert.iff_status, "LOW"),
    }
