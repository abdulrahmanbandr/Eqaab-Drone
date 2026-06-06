"""
Eqaab edge node — central configuration.

ALL tunables live here and are sourced from environment variables (optionally loaded
from a .env file). Nothing operational is hardcoded — no URLs, no device paths, no
model paths. Copy .env.example -> .env on the Pi and fill in real values.

Design notes
------------
* Lightweight: only python-dotenv is needed to parse the .env file; everything else is
  stdlib. We deliberately avoid YAML/pydantic-settings here to keep the import graph and
  RAM footprint small on the Pi 5.
* `drone_id` is LOGGING-ONLY. The real GCS schema (schemas.py) has no drone_id field on
  the wire, so it must never be serialized into a telemetry/detection message.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

try:
    # Optional: load a local .env if present. Never required at runtime.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional
    pass


# ──────────────────────────────────────────────
# env parsing helpers
# ──────────────────────────────────────────────

def _str(key: str, default: str) -> str:
    val = os.getenv(key)
    return val if val is not None and val != "" else default


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def _float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def _bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _csv(key: str, default: str) -> List[str]:
    raw = _str(key, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ──────────────────────────────────────────────
# Sub-configs
# ──────────────────────────────────────────────

@dataclass
class CameraConfig:
    # "picamera2" (Pi Camera Module 3, default) or "opencv" (USB/UVC webcam).
    source: str = field(default_factory=lambda: _str("CAMERA_SOURCE", "picamera2"))
    # Capture resolution. Keep modest; the detector downscales to IMG_SIZE anyway.
    width: int = field(default_factory=lambda: _int("CAMERA_WIDTH", 1280))
    height: int = field(default_factory=lambda: _int("CAMERA_HEIGHT", 720))
    fps: int = field(default_factory=lambda: _int("CAMERA_FPS", 30))
    # OpenCV device index (only used when source == "opencv").
    device_index: int = field(default_factory=lambda: _int("CAMERA_DEVICE_INDEX", 0))
    # picamera2 sensor: optional horizontal/vertical flip for the mounted orientation.
    hflip: bool = field(default_factory=lambda: _bool("CAMERA_HFLIP", False))
    vflip: bool = field(default_factory=lambda: _bool("CAMERA_VFLIP", False))


@dataclass
class DetectorConfig:
    # Path to the exported model. Prefer an NCNN export dir ("best_ncnn_model") or an
    # ONNX file ("best.onnx"). Falls back to "best.pt" if that's all that's available.
    model_path: str = field(default_factory=lambda: _str("MODEL_PATH", "models/best_ncnn_model"))
    # Inference square input size — 320 (fast) or 416 (more accurate). NOT 640.
    img_size: int = field(default_factory=lambda: _int("IMG_SIZE", 320))
    conf_threshold: float = field(default_factory=lambda: _float("CONF_THRESHOLD", 0.45))
    iou_threshold: float = field(default_factory=lambda: _float("IOU_THRESHOLD", 0.45))
    # Run YOLO every Nth captured frame; DeepSort coasts on the frames in between.
    detect_every_n: int = field(default_factory=lambda: _int("DETECT_EVERY_N", 3))
    # Class id -> name mapping for the unified custom model (drone=0, person=1, car=2).
    class_names: List[str] = field(default_factory=lambda: _csv("CLASS_NAMES", "drone,person,car"))


@dataclass
class MavlinkConfig:
    # e.g. "/dev/ttyACM0", "/dev/serial0", or "udp:127.0.0.1:14540".
    connection: str = field(default_factory=lambda: _str("MAVLINK_CONNECTION", "/dev/ttyACM0"))
    baud: int = field(default_factory=lambda: _int("MAVLINK_BAUD", 921600))
    # Seconds to wait for the PX4 heartbeat before giving up a connection attempt.
    heartbeat_timeout: float = field(default_factory=lambda: _float("MAVLINK_HEARTBEAT_TIMEOUT", 10.0))


@dataclass
class GcsConfig:
    # Outbound WebSocket (WSS) to the Ground Control Station. REQUIRED at deploy time.
    ws_url: str = field(default_factory=lambda: _str("GCS_WS_URL", "wss://CHANGE_ME.example.com/ws/drone"))
    # Optional bearer token (sent as Authorization header). Empty = no auth header.
    auth_token: str = field(default_factory=lambda: _str("GCS_AUTH_TOKEN", ""))
    # Telemetry cadence — fixed 1 Hz by design, independent of vision FPS.
    telemetry_hz: float = field(default_factory=lambda: _float("TELEMETRY_HZ", 1.0))
    # Auto-reconnect backoff (seconds): start, multiplier, cap.
    reconnect_initial: float = field(default_factory=lambda: _float("RECONNECT_INITIAL_S", 1.0))
    reconnect_max: float = field(default_factory=lambda: _float("RECONNECT_MAX_S", 30.0))


@dataclass
class GeoConfig:
    """Camera geometry for projecting target pixels onto ground lat/lon."""
    # Field of view of the lens, degrees. Defaults = Pi Cam Module 3 standard lens.
    # Wide lens is roughly HFOV 102 / VFOV 67 — override via env if fitted.
    hfov_deg: float = field(default_factory=lambda: _float("CAM_HFOV_DEG", 66.0))
    vfov_deg: float = field(default_factory=lambda: _float("CAM_VFOV_DEG", 41.0))
    # If true, use live gimbal orientation from MAVLink when available.
    use_mavlink_gimbal: bool = field(default_factory=lambda: _bool("USE_MAVLINK_GIMBAL", True))
    # Fixed-mount fallback when no gimbal feedback: pitch DOWN from horizon (deg),
    # yaw relative to the drone nose (deg, + = right).
    mount_pitch_down_deg: float = field(default_factory=lambda: _float("CAM_MOUNT_PITCH_DOWN_DEG", 30.0))
    mount_yaw_deg: float = field(default_factory=lambda: _float("CAM_MOUNT_YAW_DEG", 0.0))


@dataclass
class IffConfig:
    """Inputs to the single, isolated IFF policy function (see iff.py)."""
    # Friendly drone identifiers (allowlist). Detected drones not matched here -> unknown.
    friendly_drone_ids: List[str] = field(default_factory=lambda: _csv("FRIENDLY_DRONE_IDS", "EQAAB-01,EQAAB-02"))
    # Minimum confidence for a detection to be eligible for a hostile classification.
    hostile_min_confidence: float = field(default_factory=lambda: _float("IFF_HOSTILE_MIN_CONF", 0.60))


@dataclass
class TrackerConfig:
    max_age: int = field(default_factory=lambda: _int("TRACK_MAX_AGE", 30))
    n_init: int = field(default_factory=lambda: _int("TRACK_N_INIT", 3))
    max_cosine_distance: float = field(default_factory=lambda: _float("TRACK_MAX_COSINE_DIST", 0.2))
    # Only emit an alert/detection once a track is "confirmed" and seen this many times.
    confirm_hits: int = field(default_factory=lambda: _int("TRACK_CONFIRM_HITS", 3))


@dataclass
class Config:
    drone_id: str = field(default_factory=lambda: _str("DRONE_ID", "eqaab-01"))  # logging only
    log_level: str = field(default_factory=lambda: _str("LOG_LEVEL", "INFO"))

    camera: CameraConfig = field(default_factory=CameraConfig)
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    mavlink: MavlinkConfig = field(default_factory=MavlinkConfig)
    gcs: GcsConfig = field(default_factory=GcsConfig)
    geo: GeoConfig = field(default_factory=GeoConfig)
    iff: IffConfig = field(default_factory=IffConfig)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)


def load_config() -> Config:
    """Build a Config from the current environment (.env already loaded at import)."""
    return Config()
