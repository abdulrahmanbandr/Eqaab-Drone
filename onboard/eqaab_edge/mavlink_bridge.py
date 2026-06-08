"""
Module 5 — MAVLink telemetry bridge (pymavlink, PX4/Pixhawk).

A dedicated thread reads MAVLink from the flight controller and keeps a single, thread-safe
`TelemetryState` snapshot up to date. Readers (the 1 Hz telemetry timer, the geo-projection
for alerts) just call `get_state()` — they never touch the serial link or block on it.

Design
------
* `pymavlink` ONLY — no ROS 2 / MAVROS (per project rules). Lightweight, stdlib + pymavlink.
* Own thread, fully decoupled from vision and from the WebSocket I/O.
* Auto-reconnect with backoff if the link drops or the heartbeat times out.
* Imports pymavlink lazily so non-flight tooling/tests don't need it installed.

RC OVERRIDE NOTE (read this):
    On PX4, manual RC (2.4 GHz radio straight into the Pixhawk) is a HARDWARE-LEVEL
    priority and overrides everything this companion computer does. This bridge only
    *reads* telemetry; command sending lives in the command module and must likewise
    never attempt to suppress or bypass RC override.

This module is telemetry-only. The wire mapping into schemas.py happens in the message
builder; here we keep neutral, source-accurate fields.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from .config import MavlinkConfig

logger = logging.getLogger(__name__)

# How often (Hz) we ask PX4 to stream each message. Kept modest — telemetry to the GCS is
# only 1 Hz, but a little headroom keeps values fresh for alert geo-projection.
_STREAM_RATES_HZ = {
    "GLOBAL_POSITION_INT": 5.0,   # lat/lon/alt/heading/velocity
    "VFR_HUD": 4.0,               # ground speed, climb, heading (backup)
    "SYS_STATUS": 2.0,            # battery %, voltage
    "BATTERY_STATUS": 1.0,        # battery % (backup / multi-cell)
    "GPS_RAW_INT": 2.0,           # fix type, satellites
    "HEARTBEAT": 1.0,             # armed flag, flight mode
    "MOUNT_ORIENTATION": 5.0,     # gimbal pitch/yaw for geo-projection (if a gimbal exists)
}


@dataclass
class TelemetryState:
    """Latest known flight telemetry. Neutral field names (mapped to the wire later)."""
    # Position / motion
    lat: Optional[float] = None          # degrees
    lon: Optional[float] = None          # degrees
    alt_rel_m: float = 0.0               # metres above launch/home
    alt_msl_m: float = 0.0               # metres above mean sea level
    heading_deg: float = 0.0             # 0–360, 0 = North
    ground_speed_ms: float = 0.0
    vertical_speed_ms: float = 0.0       # + = climbing

    # Power
    battery_pct: float = 0.0             # 0–100
    voltage_v: float = 0.0

    # GPS
    gps_fix: int = 0                     # 0=none, 2=2D, 3=3D
    satellites: int = 0

    # State
    armed: bool = False
    flight_mode: str = "HOLD"            # mapped to schemas.py FlightMode value

    # Gimbal (for target geo-projection); None = no gimbal feedback, use fixed mount.
    gimbal_depression_deg: Optional[float] = None   # + = looking down
    gimbal_yaw_deg: Optional[float] = None          # relative to nose, + = right

    # Link health
    connected: bool = False
    last_heartbeat_s: float = 0.0        # time.monotonic() of last heartbeat


# ── PX4 custom_mode decoding ────────────────────────────────────────────────
# PX4 packs main/sub mode into the HEARTBEAT custom_mode: bits 16-23 = main, 24-31 = sub.
_PX4_MAIN = {1: "MANUAL", 2: "ALTITUDE", 3: "POSITION", 4: "AUTO",
             5: "MANUAL", 6: "OFFBOARD", 7: "STABILIZED", 8: "STABILIZED"}
_PX4_AUTO_SUB = {2: "TAKEOFF", 3: "HOLD", 4: "AUTO", 5: "RTL", 6: "LAND"}


def px4_flight_mode(custom_mode: int) -> str:
    """Map a PX4 HEARTBEAT custom_mode to a schemas.py FlightMode value."""
    main = (custom_mode >> 16) & 0xFF
    sub = (custom_mode >> 24) & 0xFF
    if main == 4:  # AUTO — refine by sub-mode
        return _PX4_AUTO_SUB.get(sub, "AUTO")
    return _PX4_MAIN.get(main, "HOLD")


class MavlinkBridge:
    """Threaded pymavlink reader exposing a thread-safe TelemetryState."""

    def __init__(self, cfg: MavlinkConfig) -> None:
        self.cfg = cfg
        self._master = None
        self._state = TelemetryState()
        self._lock = threading.Lock()
        self._send_lock = threading.Lock()   # serialize command writes to the link
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._mavutil = None  # cached pymavlink.mavutil module

    # --- lifecycle -----------------------------------------------------
    def start(self) -> None:
        if self._thread is not None:
            return
        from pymavlink import mavutil  # lazy import (only needed in flight)
        self._mavutil = mavutil
        self._running.set()
        self._thread = threading.Thread(target=self._loop, name="mavlink-bridge", daemon=True)
        self._thread.start()
        logger.info("MAVLink bridge started (%s)", self.cfg.connection)

    def stop(self) -> None:
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        self._close()
        logger.info("MAVLink bridge stopped")

    def get_state(self) -> TelemetryState:
        """Return a copy of the latest telemetry (cheap; safe to call at any rate)."""
        with self._lock:
            # dataclass is flat; shallow copy via replace-free copy of fields.
            return TelemetryState(**vars(self._state))

    # --- command senders (used by the command module) -----------------
    #
    # RC OVERRIDE: these issue OFFBOARD/AUTO intent to PX4. They NEVER send
    # RC_CHANNELS_OVERRIDE and never attempt to defeat the pilot's radio. On PX4,
    # hardware RC is a higher priority than anything sent here — if the pilot takes
    # the sticks, the flight controller ignores these commands. That is by design.

    def _can_send(self) -> bool:
        if self._master is None or not self._state.connected:
            logger.warning("Cannot send command — MAVLink not connected")
            return False
        return True

    def send_command_long(self, command_id: int, p1: float = 0, p2: float = 0,
                          p3: float = 0, p4: float = 0, p5: float = 0,
                          p6: float = 0, p7: float = 0) -> bool:
        """Send a COMMAND_LONG to the flight controller. Returns False if not connected."""
        if not self._can_send():
            return False
        m = self._master
        try:
            with self._send_lock:
                m.mav.command_long_send(m.target_system, m.target_component,
                                        command_id, 0, p1, p2, p3, p4, p5, p6, p7)
            return True
        except Exception:
            logger.exception("command_long_send failed (id=%s)", command_id)
            return False

    def set_px4_mode(self, main_mode: int, sub_mode: int = 0) -> bool:
        """Switch PX4 flight mode via DO_SET_MODE (custom main/sub mode)."""
        mavutil = self._mavutil
        base = mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
        return self.send_command_long(mavutil.mavlink.MAV_CMD_DO_SET_MODE,
                                      base, main_mode, sub_mode)

    def reposition(self, lat: float, lon: float, alt: float) -> bool:
        """Fly to a lat/lon/alt (relative) via DO_REPOSITION (COMMAND_INT)."""
        if not self._can_send():
            return False
        m, mavutil = self._master, self._mavutil
        try:
            with self._send_lock:
                m.mav.command_int_send(
                    m.target_system, m.target_component,
                    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                    mavutil.mavlink.MAV_CMD_DO_REPOSITION, 0, 0,
                    -1, 0, 0, float("nan"),         # speed=-1 (default), flags, reserved, yaw=keep
                    int(lat * 1e7), int(lon * 1e7), float(alt),
                )
            return True
        except Exception:
            logger.exception("reposition failed")
            return False

    # --- connection ----------------------------------------------------
    def _connect(self) -> bool:
        mavutil = self._mavutil
        try:
            self._master = mavutil.mavlink_connection(
                self.cfg.connection, baud=self.cfg.baud, source_system=255
            )
            logger.info("Waiting for PX4 heartbeat (timeout %.0fs)...", self.cfg.heartbeat_timeout)
            hb = self._master.wait_heartbeat(timeout=self.cfg.heartbeat_timeout)
            if hb is None:
                logger.warning("No heartbeat — will retry")
                self._close()
                return False
            logger.info("Heartbeat from system %d component %d", self._master.target_system,
                        self._master.target_component)
            self._request_streams()
            with self._lock:
                self._state.connected = True
                self._state.last_heartbeat_s = time.monotonic()
            return True
        except Exception:
            logger.exception("MAVLink connect failed")
            self._close()
            return False

    def _request_streams(self) -> None:
        """Ask PX4 to emit the messages we need at the rates above (SET_MESSAGE_INTERVAL)."""
        mavutil = self._mavutil
        m = self._master
        for name, hz in _STREAM_RATES_HZ.items():
            try:
                msg_id = getattr(mavutil.mavlink, f"MAVLINK_MSG_ID_{name}")
                interval_us = int(1_000_000 / hz)
                m.mav.command_long_send(
                    m.target_system, m.target_component,
                    mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0,
                    msg_id, interval_us, 0, 0, 0, 0, 0,
                )
            except Exception:
                logger.debug("Could not request stream %s", name, exc_info=True)

    def _close(self) -> None:
        if self._master is not None:
            try:
                self._master.close()
            except Exception:
                pass
            self._master = None
        with self._lock:
            self._state.connected = False

    # --- read loop -----------------------------------------------------
    def _loop(self) -> None:
        backoff = 1.0
        while self._running.is_set():
            if self._master is None:
                if not self._connect():
                    time.sleep(min(backoff, self.cfg.heartbeat_timeout))
                    backoff = min(backoff * 2, 30.0)
                    continue
                backoff = 1.0

            try:
                msg = self._master.recv_match(blocking=True, timeout=1.0)
            except Exception:
                logger.exception("MAVLink recv error; reconnecting")
                self._close()
                continue

            now = time.monotonic()
            # Heartbeat-timeout watchdog: if PX4 goes quiet, drop and reconnect.
            with self._lock:
                last_hb = self._state.last_heartbeat_s
            if last_hb and (now - last_hb) > self.cfg.heartbeat_timeout:
                logger.warning("Heartbeat lost (%.1fs) — reconnecting", now - last_hb)
                self._close()
                continue

            if msg is not None:
                self._ingest(msg, now)

    def _ingest(self, msg, now: float) -> None:
        """Update state from one MAVLink message. Single writer (this thread)."""
        mtype = msg.get_type()
        with self._lock:
            s = self._state
            if mtype == "HEARTBEAT":
                s.last_heartbeat_s = now
                s.connected = True
                s.armed = bool(msg.base_mode & self._mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                s.flight_mode = px4_flight_mode(msg.custom_mode)
            elif mtype == "GLOBAL_POSITION_INT":
                s.lat = msg.lat / 1e7
                s.lon = msg.lon / 1e7
                s.alt_msl_m = msg.alt / 1000.0
                s.alt_rel_m = msg.relative_alt / 1000.0
                s.heading_deg = (msg.hdg / 100.0) % 360.0 if msg.hdg != 65535 else s.heading_deg
                s.vertical_speed_ms = -msg.vz / 100.0   # vz is +down in NED → flip to +up
            elif mtype == "VFR_HUD":
                s.ground_speed_ms = float(msg.groundspeed)
                # Prefer GLOBAL_POSITION_INT heading; VFR_HUD is a backup if hdg was unset.
                if s.heading_deg == 0.0:
                    s.heading_deg = float(msg.heading) % 360.0
            elif mtype == "SYS_STATUS":
                if msg.battery_remaining != -1:
                    s.battery_pct = float(msg.battery_remaining)
                if msg.voltage_battery not in (0, 65535):
                    s.voltage_v = msg.voltage_battery / 1000.0
            elif mtype == "BATTERY_STATUS":
                if msg.battery_remaining != -1:
                    s.battery_pct = float(msg.battery_remaining)
            elif mtype == "GPS_RAW_INT":
                s.gps_fix = int(msg.fix_type)
                s.satellites = int(msg.satellites_visible)
            elif mtype == "MOUNT_ORIENTATION":
                # MOUNT_ORIENTATION pitch: + up / − down. Depression = −pitch.
                s.gimbal_depression_deg = -float(msg.pitch)
                s.gimbal_yaw_deg = float(msg.yaw)
