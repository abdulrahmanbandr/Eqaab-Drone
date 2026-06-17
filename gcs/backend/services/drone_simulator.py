"""
Eqaab GCS — Drone Simulator

Simulates a drone flying a patrol mission near Taif.
Generates realistic telemetry, detections, and responds to commands.
Replace this with the real drone WebSocket connection in production.
"""

import asyncio
import math
import random
import time
import logging
import uuid
from typing import Optional

from models.schemas import (
    TelemetryMessage,
    DetectionMessage,
    BoundingBox,
    EventMessage,
    CommandType,
    CommandResponse,
    FlightMode,
    DroneState,
    ThreatLevel,
    IFFStatus,
)
import config

logger = logging.getLogger("eqaab.sim")


class DroneSimulator:
    """
    Simulates drone state and flight behavior.

    States: IDLE → ARMED → TAKING_OFF → FLYING → RETURNING → LANDING → LANDED
    The simulator flies between patrol waypoints, drains battery,
    and generates random detections.
    """

    def __init__(self):
        # Position
        self.lat = config.HOME_LAT
        self.lon = config.HOME_LON
        self.alt = 0.0
        self.heading = 0.0

        # Motion
        self.speed = 0.0
        self.vertical_speed = 0.0
        self.target_speed = 5.0             # m/s cruise speed

        # Battery
        self.battery = config.BATTERY_FULL
        self.voltage = 16.8                 # 4S LiPo full

        # GPS (simulated)
        self.gps_fix = 3
        self.satellites = 14

        # State
        self.armed = False
        self.flight_mode = FlightMode.HOLD
        self.drone_state = DroneState.IDLE

        # Mission
        self.waypoints = config.PATROL_WAYPOINTS
        self.current_wp_index = 0
        self.mission_active = False
        self.mission_paused = False

        # RTL
        self.rtl_active = False

        # Tracking
        self._track_counter = 0
        self._last_detection_time = 0.0
        self._start_time = time.time()
        self._last_update = time.time()

        # Target position for goto commands
        self._goto_target: Optional[dict] = None

    # ──────────────────────────────────────────
    # State update (called at TELEMETRY_RATE_HZ)
    # ──────────────────────────────────────────

    def update(self, dt: float) -> TelemetryMessage:
        """Advance simulation by dt seconds. Returns updated telemetry."""

        now = time.time()

        # Battery drain (faster when flying)
        if self.armed:
            drain_rate = config.BATTERY_DRAIN_PER_SEC
            if self.speed > 0:
                drain_rate *= 1.5
            self.battery = max(0.0, self.battery - drain_rate * dt)
            self.voltage = 13.0 + (self.battery / 100.0) * 3.8

            # Auto-RTL on low battery
            if self.battery <= config.BATTERY_RTL_THRESHOLD and not self.rtl_active:
                self._trigger_rtl("Low battery auto-RTL")

        # State machine
        if self.drone_state == DroneState.TAKING_OFF:
            self._update_takeoff(dt)
        elif self.drone_state == DroneState.FLYING:
            self._update_flying(dt)
        elif self.drone_state == DroneState.RETURNING:
            self._update_rtl(dt)
        elif self.drone_state == DroneState.LANDING:
            self._update_landing(dt)

        # Add GPS noise
        lat_noise = random.gauss(0, 0.000002)
        lon_noise = random.gauss(0, 0.000002)

        return TelemetryMessage(
            timestamp=now,
            lat=self.lat + lat_noise,
            lon=self.lon + lon_noise,
            alt=round(self.alt, 1),
            heading=round(self.heading % 360, 1),
            speed=round(self.speed, 1),
            vertical_speed=round(self.vertical_speed, 1),
            battery=round(self.battery, 1),
            voltage=round(self.voltage, 2),
            gps_fix=self.gps_fix,
            satellites=self.satellites + random.randint(-2, 2),
            armed=self.armed,
            flight_mode=self.flight_mode,
            drone_state=self.drone_state,
            signal_latency_ms=random.randint(45, 140),
        )

    # ──────────────────────────────────────────
    # Flight state handlers
    # ──────────────────────────────────────────

    def _update_takeoff(self, dt: float):
        target_alt = self._goto_target.get("alt", 10.0) if self._goto_target else 10.0
        self.vertical_speed = 2.0  # climb at 2 m/s
        self.alt += self.vertical_speed * dt
        self.speed = 0.0

        if self.alt >= target_alt:
            self.alt = target_alt
            self.vertical_speed = 0.0
            self.drone_state = DroneState.FLYING
            self.flight_mode = FlightMode.AUTO if self.mission_active else FlightMode.HOLD
            logger.info(f"Takeoff complete at {self.alt}m")

    def _update_flying(self, dt: float):
        self.vertical_speed = 0.0

        if self.mission_paused:
            self.speed = 0.0
            self.flight_mode = FlightMode.HOLD
            return

        # Determine target
        target = None
        if self._goto_target:
            target = self._goto_target
        elif self.mission_active and self.waypoints:
            target = self.waypoints[self.current_wp_index]

        if target is None:
            # No target — just hover
            self.speed = 0.0
            self.flight_mode = FlightMode.HOLD
            return

        self.flight_mode = FlightMode.AUTO

        # Navigate toward target
        arrived = self._move_toward(
            target["lat"], target["lon"], target.get("alt", self.alt), dt
        )

        if arrived:
            if self._goto_target:
                # Single goto complete
                self._goto_target = None
                self.speed = 0.0
                self.flight_mode = FlightMode.HOLD
                logger.info("Goto waypoint reached")
            elif self.mission_active:
                # Advance to next patrol waypoint (loop)
                self.current_wp_index = (self.current_wp_index + 1) % len(self.waypoints)
                logger.info(f"Waypoint reached, next: {self.current_wp_index}")

    def _update_rtl(self, dt: float):
        self.flight_mode = FlightMode.RTL

        # First climb to safe RTL altitude
        rtl_alt = 30.0
        if self.alt < rtl_alt:
            self.vertical_speed = 2.0
            self.alt += self.vertical_speed * dt
            self.speed = 0.0
            return

        # Fly toward home
        arrived = self._move_toward(
            config.HOME_LAT, config.HOME_LON, rtl_alt, dt
        )

        if arrived:
            self.drone_state = DroneState.LANDING
            logger.info("Arrived at home, landing")

    def _update_landing(self, dt: float):
        self.flight_mode = FlightMode.LAND
        self.vertical_speed = -1.5
        self.speed = 0.0
        self.alt += self.vertical_speed * dt

        if self.alt <= 0.0:
            self.alt = 0.0
            self.vertical_speed = 0.0
            self.speed = 0.0
            self.armed = False
            self.drone_state = DroneState.LANDED
            self.rtl_active = False
            self.mission_active = False
            self._goto_target = None
            logger.info("Landed and disarmed")

    # ──────────────────────────────────────────
    # Navigation helper
    # ──────────────────────────────────────────

    def _move_toward(self, target_lat: float, target_lon: float,
                     target_alt: float, dt: float) -> bool:
        """Move toward target. Returns True if arrived."""

        dlat = target_lat - self.lat
        dlon = target_lon - self.lon
        dalt = target_alt - self.alt

        # Approximate distance in meters (lat/lon to meters near Taif)
        dist_lat = dlat * 111320
        dist_lon = dlon * 111320 * math.cos(math.radians(self.lat))
        horizontal_dist = math.sqrt(dist_lat ** 2 + dist_lon ** 2)

        # Update heading
        if horizontal_dist > 0.5:
            self.heading = math.degrees(math.atan2(dist_lon, dist_lat)) % 360

        # Check arrival (within 2 meters)
        if horizontal_dist < 2.0 and abs(dalt) < 1.0:
            self.speed = 0.0
            self.vertical_speed = 0.0
            return True

        # Move at cruise speed
        self.speed = min(self.target_speed, horizontal_dist)
        move_dist = self.speed * dt  # meters to move this tick

        if horizontal_dist > 0:
            ratio = min(move_dist / horizontal_dist, 1.0)
            self.lat += dlat * ratio
            self.lon += dlon * ratio

        # Vertical
        if abs(dalt) > 0.5:
            self.vertical_speed = 1.5 if dalt > 0 else -1.5
            self.alt += self.vertical_speed * dt
        else:
            self.alt = target_alt
            self.vertical_speed = 0.0

        return False

    # ──────────────────────────────────────────
    # Detection generator
    # ──────────────────────────────────────────

    def maybe_generate_detection(self) -> Optional[DetectionMessage]:
        """Randomly generate a detection if enough time has passed."""

        if self.drone_state not in (DroneState.FLYING, DroneState.RETURNING):
            return None

        now = time.time()
        elapsed = now - self._last_detection_time

        # Random interval with some variance
        interval = config.DETECTION_INTERVAL_SEC + random.uniform(-3, 5)
        if elapsed < interval:
            return None

        self._last_detection_time = now
        self._track_counter += 1

        # Pick detection class
        det_class = random.choices(
            config.DETECTION_CLASSES,
            weights=config.DETECTION_WEIGHTS,
            k=1,
        )[0]

        # Confidence varies by class
        if det_class == "person":
            confidence = random.uniform(0.75, 0.95)
            model = "yolov8n"
        elif det_class == "car":
            confidence = random.uniform(0.80, 0.96)
            model = "yolov8n"
        else:  # drone
            confidence = random.uniform(0.70, 0.94)
            model = "best"

        # Simulated bounding box
        cx, cy = random.randint(100, 540), random.randint(80, 400)
        w, h = random.randint(40, 120), random.randint(40, 150)
        bbox = BoundingBox(x1=cx, y1=cy, x2=cx + w, y2=cy + h)

        # Target GPS (offset from drone position)
        offset_lat = random.uniform(-0.0008, 0.0008)
        offset_lon = random.uniform(-0.0008, 0.0008)

        # IFF check for drones
        iff_status = IFFStatus.UNKNOWN
        iff_id = None
        threat = ThreatLevel.LOW

        if det_class == "drone":
            # 30% chance it's a friendly drone
            if random.random() < 0.3:
                iff_status = IFFStatus.FRIENDLY
                iff_id = random.choice(config.FRIENDLY_DRONE_IDS)
                threat = ThreatLevel.LOW
            else:
                iff_status = IFFStatus.UNKNOWN
                threat = ThreatLevel.HIGH
        elif det_class == "person":
            threat = ThreatLevel.MEDIUM
        elif det_class == "car":
            threat = ThreatLevel.LOW

        return DetectionMessage(
            timestamp=now,
            detection_class=det_class,
            confidence=round(confidence, 2),
            track_id=self._track_counter,
            bbox=bbox,
            model_source=model,
            target_lat=round(self.lat + offset_lat, 6),
            target_lon=round(self.lon + offset_lon, 6),
            iff_status=iff_status,
            iff_id=iff_id,
            threat_level=threat,
        )

    # ──────────────────────────────────────────
    # Command handler
    # ──────────────────────────────────────────

    def handle_command(self, command: CommandType, params: dict) -> CommandResponse:
        """Process a command and return acknowledgment."""

        handler = {
            CommandType.ARM: self._cmd_arm,
            CommandType.DISARM: self._cmd_disarm,
            CommandType.TAKEOFF: self._cmd_takeoff,
            CommandType.LAND: self._cmd_land,
            CommandType.RTL: self._cmd_rtl,
            CommandType.HOLD: self._cmd_hold,
            CommandType.GOTO: self._cmd_goto,
            CommandType.SET_MODE: self._cmd_set_mode,
            CommandType.SET_SPEED: self._cmd_set_speed,
            CommandType.START_MISSION: self._cmd_start_mission,
            CommandType.PAUSE_MISSION: self._cmd_pause_mission,
        }.get(command)

        if handler is None:
            return CommandResponse(
                command=command, success=False,
                message=f"Unknown command: {command}"
            )

        return handler(params)

    def _cmd_arm(self, params: dict) -> CommandResponse:
        if self.battery < 10:
            return CommandResponse(
                command=CommandType.ARM, success=False,
                message="Battery too low to arm"
            )
        if self.gps_fix < 3:
            return CommandResponse(
                command=CommandType.ARM, success=False,
                message="No GPS 3D fix"
            )
        self.armed = True
        self.drone_state = DroneState.ARMED
        logger.info("Drone ARMED")
        return CommandResponse(
            command=CommandType.ARM, success=True,
            message="Drone armed successfully"
        )

    def _cmd_disarm(self, params: dict) -> CommandResponse:
        if self.alt > 1.0:
            return CommandResponse(
                command=CommandType.DISARM, success=False,
                message="Cannot disarm while airborne"
            )
        self.armed = False
        self.drone_state = DroneState.IDLE
        self.mission_active = False
        logger.info("Drone DISARMED")
        return CommandResponse(
            command=CommandType.DISARM, success=True,
            message="Drone disarmed"
        )

    def _cmd_takeoff(self, params: dict) -> CommandResponse:
        if not self.armed:
            return CommandResponse(
                command=CommandType.TAKEOFF, success=False,
                message="Drone must be armed first"
            )
        if self.drone_state not in (DroneState.ARMED, DroneState.LANDED):
            return CommandResponse(
                command=CommandType.TAKEOFF, success=False,
                message=f"Cannot takeoff from state: {self.drone_state}"
            )
        alt = params.get("altitude", 10.0)
        self._goto_target = {"lat": self.lat, "lon": self.lon, "alt": alt}
        self.drone_state = DroneState.TAKING_OFF
        self.flight_mode = FlightMode.TAKEOFF
        logger.info(f"Taking off to {alt}m")
        return CommandResponse(
            command=CommandType.TAKEOFF, success=True,
            message=f"Taking off to {alt}m"
        )

    def _cmd_land(self, params: dict) -> CommandResponse:
        if self.drone_state not in (DroneState.FLYING, DroneState.RETURNING):
            return CommandResponse(
                command=CommandType.LAND, success=False,
                message="Drone is not airborne"
            )
        self.drone_state = DroneState.LANDING
        self.mission_active = False
        self.rtl_active = False
        logger.info("Landing at current position")
        return CommandResponse(
            command=CommandType.LAND, success=True,
            message="Landing initiated"
        )

    def _cmd_rtl(self, params: dict) -> CommandResponse:
        if not self.armed:
            return CommandResponse(
                command=CommandType.RTL, success=False,
                message="Drone is not armed"
            )
        self._trigger_rtl("Operator RTL command")
        return CommandResponse(
            command=CommandType.RTL, success=True,
            message="Returning to launch"
        )

    def _cmd_hold(self, params: dict) -> CommandResponse:
        if self.drone_state == DroneState.FLYING:
            self.mission_paused = True
            self.flight_mode = FlightMode.HOLD
            self.speed = 0.0
            self._goto_target = None
            logger.info("Holding position")
            return CommandResponse(
                command=CommandType.HOLD, success=True,
                message="Holding position"
            )
        return CommandResponse(
            command=CommandType.HOLD, success=False,
            message="Drone is not flying"
        )

    def _cmd_goto(self, params: dict) -> CommandResponse:
        lat = params.get("lat")
        lon = params.get("lon")
        alt = params.get("alt", self.alt)
        if lat is None or lon is None:
            return CommandResponse(
                command=CommandType.GOTO, success=False,
                message="Missing lat/lon parameters"
            )
        if self.drone_state not in (DroneState.FLYING,):
            return CommandResponse(
                command=CommandType.GOTO, success=False,
                message="Drone must be flying"
            )
        self._goto_target = {"lat": lat, "lon": lon, "alt": alt}
        self.mission_paused = False
        self.mission_active = False
        logger.info(f"Going to {lat}, {lon} at {alt}m")
        return CommandResponse(
            command=CommandType.GOTO, success=True,
            message=f"Navigating to ({lat:.4f}, {lon:.4f})"
        )

    def _cmd_set_mode(self, params: dict) -> CommandResponse:
        mode = params.get("mode", "HOLD")
        try:
            self.flight_mode = FlightMode(mode)
            return CommandResponse(
                command=CommandType.SET_MODE, success=True,
                message=f"Mode set to {mode}"
            )
        except ValueError:
            return CommandResponse(
                command=CommandType.SET_MODE, success=False,
                message=f"Invalid mode: {mode}"
            )

    def _cmd_set_speed(self, params: dict) -> CommandResponse:
        speed = params.get("speed", 5.0)
        self.target_speed = max(1.0, min(15.0, speed))
        return CommandResponse(
            command=CommandType.SET_SPEED, success=True,
            message=f"Speed set to {self.target_speed} m/s"
        )

    def _cmd_start_mission(self, params: dict) -> CommandResponse:
        if self.drone_state not in (DroneState.FLYING, DroneState.ARMED):
            return CommandResponse(
                command=CommandType.START_MISSION, success=False,
                message="Drone must be flying or armed"
            )
        self.mission_active = True
        self.mission_paused = False
        self.current_wp_index = 0
        self._goto_target = None
        logger.info("Mission started")
        return CommandResponse(
            command=CommandType.START_MISSION, success=True,
            message=f"Mission started with {len(self.waypoints)} waypoints"
        )

    def _cmd_pause_mission(self, params: dict) -> CommandResponse:
        if self.mission_active:
            self.mission_paused = True
            return CommandResponse(
                command=CommandType.PAUSE_MISSION, success=True,
                message="Mission paused"
            )
        return CommandResponse(
            command=CommandType.PAUSE_MISSION, success=False,
            message="No active mission"
        )

    def _trigger_rtl(self, reason: str):
        self.rtl_active = True
        self.drone_state = DroneState.RETURNING
        self.mission_active = False
        self.mission_paused = False
        self._goto_target = None
        logger.info(f"RTL triggered: {reason}")
