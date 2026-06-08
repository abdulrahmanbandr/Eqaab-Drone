"""
Module 7 — Command handling (GCS → drone → PX4).

Receives "command" messages from the GCS and dispatches them to safe MAVLink handlers on
the flight controller. Wired as the `on_command` callback of the WebSocket client; it runs
on an executor thread so a slow link/command never stalls telemetry or detections.

Command vocabulary
------------------
The authoritative command set is schemas.py `CommandType` (lowercase): arm, disarm, takeoff,
land, rtl, hold, goto, set_mode, set_speed, start_mission, pause_mission. We ALSO accept the
on-board spec's aliases (RTH→rtl, PAUSE→pause_mission, RESUME→start_mission, TAKEOFF→takeoff,
…) and tolerate either `params` or `parameters` — so whatever the GCS sends, we cope.

UPLOAD_MISSION / SET_GEOFENCE are acknowledged but not yet executed (they need the multi-
message MAVLink mission/fence protocol); they're explicit, logged no-ops, never silent.

╔══════════════════════════════════════════════════════════════════════════════════════╗
║ RC OVERRIDE IS HARDWARE-LEVEL AND ALWAYS WINS.                                        ║
║ On PX4, the pilot's 2.4 GHz RC link goes straight to the Pixhawk and overrides every  ║
║ command in this file. Nothing here sends RC_CHANNELS_OVERRIDE or otherwise tries to   ║
║ suppress, mask, or defeat manual control. If the pilot grabs the sticks, the flight   ║
║ controller ignores us. Never change that.                                            ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from .config import Config
from .mavlink_bridge import MavlinkBridge

logger = logging.getLogger(__name__)

# PX4 custom main modes (for DO_SET_MODE).
_MAIN_MANUAL, _MAIN_ALT, _MAIN_POS, _MAIN_AUTO, _MAIN_OFFBOARD, _MAIN_STAB = 1, 2, 3, 4, 6, 7
# PX4 AUTO sub-modes.
_AUTO_TAKEOFF, _AUTO_HOLD, _AUTO_MISSION, _AUTO_RTL, _AUTO_LAND = 2, 3, 4, 5, 6

# set_mode string (schemas.py FlightMode) → PX4 (main, sub).
_MODE_MAP = {
    "MANUAL": (_MAIN_MANUAL, 0), "ALTITUDE": (_MAIN_ALT, 0), "POSITION": (_MAIN_POS, 0),
    "OFFBOARD": (_MAIN_OFFBOARD, 0), "STABILIZED": (_MAIN_STAB, 0),
    "AUTO": (_MAIN_AUTO, _AUTO_MISSION), "HOLD": (_MAIN_AUTO, _AUTO_HOLD),
    "RTL": (_MAIN_AUTO, _AUTO_RTL), "LAND": (_MAIN_AUTO, _AUTO_LAND),
    "TAKEOFF": (_MAIN_AUTO, _AUTO_TAKEOFF),
}

# Aliases (on-board spec / convenience) → canonical schemas.py command name.
_ALIASES = {
    "rth": "rtl", "return_to_home": "rtl", "return_to_launch": "rtl",
    "pause": "pause_mission", "resume": "start_mission", "start": "start_mission",
}


class CommandHandler:
    def __init__(self, bridge: MavlinkBridge, cfg: Config,
                 send_message: Optional[Callable[[dict], None]] = None) -> None:
        self._bridge = bridge
        self._cfg = cfg
        self._send_message = send_message

    # --- entry point (called by the WS client) ------------------------
    def handle(self, msg: dict) -> None:
        raw = str(msg.get("command", "")).strip().lower()
        command = _ALIASES.get(raw, raw)
        # Accept either field name for the payload.
        params = msg.get("params") or msg.get("parameters") or {}
        logger.info("Command: %s params=%s", command, params)

        try:
            ok, detail = self._dispatch(command, params)
        except Exception as e:
            logger.exception("Command handler raised for %s", command)
            ok, detail = False, f"exception: {e}"

        status = "OK" if ok else "FAILED"
        logger.info("Command %s -> %s (%s)", command, status, detail)
        self._emit_event(f"[{status}] {command}: {detail}")

    # --- dispatch table -----------------------------------------------
    def _dispatch(self, command: str, params: dict) -> tuple[bool, str]:
        b = self._bridge
        mavutil = b._mavutil  # cached pymavlink module (None until bridge.start())
        if mavutil is None:
            return False, "MAVLink not initialised"
        mav = mavutil.mavlink

        if command == "arm":
            return b.send_command_long(mav.MAV_CMD_COMPONENT_ARM_DISARM, 1), "arm requested"
        if command == "disarm":
            return b.send_command_long(mav.MAV_CMD_COMPONENT_ARM_DISARM, 0), "disarm requested"

        if command == "takeoff":
            alt = float(params.get("altitude", params.get("alt", 15.0)))
            # NAV_TAKEOFF with explicit altitude; lat/lon NaN = use current position.
            ok = b.send_command_long(mav.MAV_CMD_NAV_TAKEOFF, 0, 0, 0,
                                     float("nan"), float("nan"), float("nan"), alt)
            return ok, f"takeoff to {alt} m"

        if command == "land":
            return b.set_px4_mode(_MAIN_AUTO, _AUTO_LAND), "AUTO.LAND"
        if command == "rtl":
            return b.set_px4_mode(_MAIN_AUTO, _AUTO_RTL), "AUTO.RTL (return to launch)"
        if command == "hold":
            return b.set_px4_mode(_MAIN_AUTO, _AUTO_HOLD), "AUTO.LOITER (hold)"
        if command in ("start_mission",):
            return b.set_px4_mode(_MAIN_AUTO, _AUTO_MISSION), "AUTO.MISSION"
        if command in ("pause_mission",):
            # PX4 pauses a mission by switching to HOLD; resume via start_mission.
            return b.set_px4_mode(_MAIN_AUTO, _AUTO_HOLD), "mission paused (HOLD)"

        if command == "set_speed":
            speed = float(params.get("speed", 5.0))
            ok = b.send_command_long(mav.MAV_CMD_DO_CHANGE_SPEED, 1, speed, -1)
            return ok, f"ground speed {speed} m/s"

        if command == "set_mode":
            mode = str(params.get("mode", "")).upper()
            if mode not in _MODE_MAP:
                return False, f"unknown mode '{mode}'"
            main, sub = _MODE_MAP[mode]
            return b.set_px4_mode(main, sub), f"mode {mode}"

        if command == "goto":
            try:
                lat = float(params["lat"]); lon = float(params["lon"])
            except (KeyError, TypeError, ValueError):
                return False, "goto requires numeric lat/lon"
            alt = float(params.get("alt", self._bridge.get_state().alt_rel_m or 15.0))
            return b.reposition(lat, lon, alt), f"goto {lat:.6f},{lon:.6f} @ {alt} m"

        # On-board spec extras not in the live CommandType enum — explicit no-ops.
        if command in ("upload_mission", "set_geofence"):
            return False, f"{command} not yet implemented (needs MAVLink mission/fence protocol)"

        return False, f"unknown command '{command}'"

    # --- feedback ------------------------------------------------------
    def _emit_event(self, message: str) -> None:
        """Send a schemas.py EventMessage back to the GCS event log (best-effort)."""
        if self._send_message is None:
            return
        try:
            self._send_message({
                "type": "event",
                "timestamp": time.time(),
                "category": "command",
                "message": message,
            })
        except Exception:
            logger.debug("Failed to emit command event", exc_info=True)
