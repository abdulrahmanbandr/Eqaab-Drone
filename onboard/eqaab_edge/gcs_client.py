"""
Module 6 — Outbound WebSocket client to the GCS.

The Pi opens ONE outbound WSS connection to the Ground Control Station and keeps it alive
for the whole flight. It:
  * sends "telemetry" on a fixed 1 Hz timer (independent of vision FPS, by design),
  * sends "detection" messages as confirmed targets arrive,
  * receives "command" messages and hands them to a callback (Module 7),
  * auto-reconnects with exponential backoff if the link drops (4G LTE is flaky),
  * estimates round-trip latency via ping/pong for the telemetry signal_latency_ms field.

Threading
---------
This runs its own asyncio event loop on a dedicated thread, fully decoupled from the vision
and MAVLink threads. Other threads feed it through thread-safe hand-offs:
  * submit_detection(dict)  — enqueue an outbound detection (called from the vision thread).
  * build_telemetry(latency)→dict — pulled by the 1 Hz timer (reads the MAVLink snapshot).

No continuous video is ever streamed — structured JSON only (project rule).
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Callable, Optional

import websockets

from .config import GcsConfig

logger = logging.getLogger(__name__)


class GcsClient:
    def __init__(
        self,
        cfg: GcsConfig,
        build_telemetry: Callable[[int], dict],
        on_command: Optional[Callable[[dict], None]] = None,
    ) -> None:
        self.cfg = cfg
        self._build_telemetry = build_telemetry
        self._on_command = on_command

        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = threading.Event()

        self._out_q: Optional[asyncio.Queue] = None   # outbound detections (loop-owned)
        self._latency_ms: int = 0
        self._ping_sent_at: Optional[float] = None
        self._connected = threading.Event()

    # --- lifecycle -----------------------------------------------------
    def start(self) -> None:
        if self._thread is not None:
            return
        self._running.set()
        self._thread = threading.Thread(target=self._run_loop, name="gcs-ws", daemon=True)
        self._thread.start()
        logger.info("GCS client started -> %s", self.cfg.ws_url)

    def stop(self) -> None:
        self._running.clear()
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        logger.info("GCS client stopped")

    @property
    def connected(self) -> bool:
        return self._connected.is_set()

    # --- thread-safe producer API -------------------------------------
    def submit_detection(self, message: dict) -> None:
        """Enqueue an outbound detection from any thread (drops if not connected yet)."""
        loop, q = self._loop, self._out_q
        if loop is None or q is None:
            return
        try:
            loop.call_soon_threadsafe(q.put_nowait, message)
        except RuntimeError:
            pass  # loop shutting down

    # --- event loop thread --------------------------------------------
    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._out_q = asyncio.Queue(maxsize=100)
        try:
            self._loop.run_until_complete(self._main())
        except Exception:
            logger.exception("GCS client loop crashed")
        finally:
            self._loop.close()

    async def _main(self) -> None:
        backoff = self.cfg.reconnect_initial
        while self._running.is_set():
            try:
                await self._session()
                backoff = self.cfg.reconnect_initial   # clean exit → reset backoff
            except Exception as e:
                logger.warning("GCS link error: %s — reconnecting in %.1fs", e, backoff)
            finally:
                self._connected.clear()
            if not self._running.is_set():
                break
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2.0, self.cfg.reconnect_max)

    async def _session(self) -> None:
        headers = {}
        if self.cfg.auth_token:
            headers["Authorization"] = f"Bearer {self.cfg.auth_token}"

        # websockets keepalive pings also help detect dead 4G links quickly.
        connect_kwargs = dict(ping_interval=20, ping_timeout=20, close_timeout=5, max_queue=64)
        try:
            ws = await websockets.connect(self.cfg.ws_url, extra_headers=headers, **connect_kwargs)
        except TypeError:
            # websockets >= 13 renamed extra_headers → additional_headers
            ws = await websockets.connect(self.cfg.ws_url, additional_headers=headers, **connect_kwargs)

        async with ws:
            self._connected.set()
            logger.info("Connected to GCS")
            # Run the per-connection tasks; the first to finish/raise tears the rest down
            # so the outer loop can reconnect.
            tasks = [
                asyncio.ensure_future(self._telemetry_timer(ws)),
                asyncio.ensure_future(self._detection_sender(ws)),
                asyncio.ensure_future(self._receiver(ws)),
                asyncio.ensure_future(self._ping_timer(ws)),
            ]
            try:
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
                for t in done:
                    if t.exception():
                        raise t.exception()
            finally:
                for t in tasks:
                    t.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

    # --- per-connection coroutines ------------------------------------
    async def _telemetry_timer(self, ws) -> None:
        """Fixed-rate telemetry, independent of vision FPS."""
        period = 1.0 / max(0.1, self.cfg.telemetry_hz)
        while True:
            msg = self._build_telemetry(self._latency_ms)
            await ws.send(json.dumps(msg))
            await asyncio.sleep(period)

    async def _detection_sender(self, ws) -> None:
        assert self._out_q is not None
        while True:
            msg = await self._out_q.get()
            await ws.send(json.dumps(msg))

    async def _ping_timer(self, ws) -> None:
        """App-level ping every 5s; latency measured from the matching pong."""
        while True:
            self._ping_sent_at = time.monotonic()
            await ws.send(json.dumps({"type": "ping", "timestamp": time.time()}))
            await asyncio.sleep(5.0)

    async def _receiver(self, ws) -> None:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            mtype = msg.get("type")
            if mtype == "pong":
                if self._ping_sent_at is not None:
                    self._latency_ms = int((time.monotonic() - self._ping_sent_at) * 1000)
            elif mtype == "command":
                self._dispatch_command(msg)
            # All other broadcast types (telemetry/event/initial_state/...) are for
            # frontend clients; the drone safely ignores them.

    def _dispatch_command(self, msg: dict) -> None:
        if self._on_command is None:
            logger.info("Command received but no handler wired: %s", msg.get("command"))
            return
        # Run the (possibly blocking) handler off the event loop so MAVLink sends
        # never stall telemetry/detection traffic.
        loop = self._loop
        if loop is not None:
            loop.run_in_executor(None, self._on_command, msg)
