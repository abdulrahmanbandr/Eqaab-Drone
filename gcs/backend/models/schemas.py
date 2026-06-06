"""
Eqaab GCS — Message Schemas

All JSON messages between drone, server, and frontend use these schemas.
The 'type' field discriminates message kind over WebSocket.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum
import time


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class FlightMode(str, Enum):
    MANUAL = "MANUAL"
    STABILIZED = "STABILIZED"
    ALTITUDE = "ALTITUDE"
    POSITION = "POSITION"
    OFFBOARD = "OFFBOARD"
    AUTO = "AUTO"
    RTL = "RTL"
    LAND = "LAND"
    HOLD = "HOLD"
    TAKEOFF = "TAKEOFF"


class DroneState(str, Enum):
    IDLE = "IDLE"
    ARMED = "ARMED"
    TAKING_OFF = "TAKING_OFF"
    FLYING = "FLYING"
    RETURNING = "RETURNING"
    LANDING = "LANDING"
    LANDED = "LANDED"
    EMERGENCY = "EMERGENCY"


class ThreatLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IFFStatus(str, Enum):
    FRIENDLY = "friendly"
    UNKNOWN = "unknown"
    HOSTILE = "hostile"


class CommandType(str, Enum):
    ARM = "arm"
    DISARM = "disarm"
    TAKEOFF = "takeoff"
    LAND = "land"
    RTL = "rtl"
    HOLD = "hold"
    GOTO = "goto"
    SET_MODE = "set_mode"
    SET_SPEED = "set_speed"
    START_MISSION = "start_mission"
    PAUSE_MISSION = "pause_mission"


# ──────────────────────────────────────────────
# Telemetry
# ──────────────────────────────────────────────

class TelemetryMessage(BaseModel):
    type: Literal["telemetry"] = "telemetry"
    timestamp: float = Field(default_factory=time.time)

    # Position
    lat: float
    lon: float
    alt: float                          # meters above launch
    heading: float                      # degrees 0-360

    # Motion
    speed: float                        # m/s ground speed
    vertical_speed: float = 0.0         # m/s (positive = climbing)

    # Battery
    battery: float                      # percentage 0-100
    voltage: float = 0.0               # volts

    # GPS
    gps_fix: int = 3                    # 0=none, 2=2D, 3=3D
    satellites: int = 0

    # State
    armed: bool = False
    flight_mode: FlightMode = FlightMode.HOLD
    drone_state: DroneState = DroneState.IDLE

    # Connection
    signal_latency_ms: int = 0          # round-trip latency estimate


# ──────────────────────────────────────────────
# Detection
# ──────────────────────────────────────────────

class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int


class DetectionMessage(BaseModel):
    type: Literal["detection"] = "detection"
    timestamp: float = Field(default_factory=time.time)

    detection_class: str                # "person", "car", "drone"
    confidence: float                   # 0.0 - 1.0
    track_id: int                       # DeepSort track ID
    bbox: BoundingBox
    model_source: str = "yolov8n"       # which model detected it

    # GPS estimate of target (projected from drone position + camera angle)
    target_lat: Optional[float] = None
    target_lon: Optional[float] = None

    # IFF (only for drone detections)
    iff_status: IFFStatus = IFFStatus.UNKNOWN
    iff_id: Optional[str] = None        # e.g. "EQAAB-02" if friendly

    # Threat assessment
    threat_level: ThreatLevel = ThreatLevel.LOW


# ──────────────────────────────────────────────
# Commands (frontend → backend → drone)
# ──────────────────────────────────────────────

class CommandRequest(BaseModel):
    command: CommandType
    params: dict = Field(default_factory=dict)
    # params examples:
    #   takeoff:  {"altitude": 10.0}
    #   goto:     {"lat": 21.49, "lon": 39.19, "alt": 50.0}
    #   set_mode: {"mode": "AUTO"}
    #   set_speed: {"speed": 5.0}


class CommandResponse(BaseModel):
    type: Literal["command_ack"] = "command_ack"
    timestamp: float = Field(default_factory=time.time)
    command: CommandType
    success: bool
    message: str = ""


# ──────────────────────────────────────────────
# Alerts (server generates from detections)
# ──────────────────────────────────────────────

class AlertMessage(BaseModel):
    type: Literal["alert"] = "alert"
    timestamp: float = Field(default_factory=time.time)
    alert_id: str
    title: str
    description: str
    threat_level: ThreatLevel
    source_track_id: Optional[int] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


# ──────────────────────────────────────────────
# System Events (for the event log)
# ──────────────────────────────────────────────

class EventMessage(BaseModel):
    type: Literal["event"] = "event"
    timestamp: float = Field(default_factory=time.time)
    category: str                       # "command", "detection", "system", "alert"
    message: str


# ──────────────────────────────────────────────
# Connection Status
# ──────────────────────────────────────────────

class ConnectionStatus(BaseModel):
    type: Literal["connection_status"] = "connection_status"
    timestamp: float = Field(default_factory=time.time)
    drone_connected: bool
    gcs_clients: int
    uptime_seconds: float


# ──────────────────────────────────────────────
# Mission Definition
# ──────────────────────────────────────────────

class Waypoint(BaseModel):
    lat: float
    lon: float
    alt: float
    speed: Optional[float] = None       # m/s, None = default
    hold_time: float = 0.0              # seconds to hover at waypoint


class MissionPlan(BaseModel):
    mission_id: str
    waypoints: list[Waypoint]
    geofence: list[dict] = Field(default_factory=list)  # [{lat, lon}, ...]
    rtl_altitude: float = 30.0


# ──────────────────────────────────────────────
# Initial State (sent to frontend on connect)
# ──────────────────────────────────────────────

class InitialState(BaseModel):
    type: Literal["initial_state"] = "initial_state"
    timestamp: float = Field(default_factory=time.time)
    home_lat: float
    home_lon: float
    geofence: list[dict]
    patrol_waypoints: list[dict]
    friendly_drone_ids: list[str]
