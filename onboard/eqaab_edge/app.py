"""
Module 8 — Application orchestrator.

Wires the four decoupled subsystems together and owns their lifecycle:

    [camera thread]      capture.py            (inside VisionPipeline)
    [inference thread]   detect → track → IFF  (VisionPipeline)
    [mavlink thread]     pymavlink telemetry/commands  (MavlinkBridge)
    [ws I/O thread]      outbound WSS to GCS           (GcsClient)

Data flow:
    MAVLink ─ telemetry ─▶ GcsClient 1 Hz timer ─▶ "telemetry"
    Vision ─ confirmed track ─▶ build_detection(+ live telemetry/geo) ─▶ GcsClient ─▶ "detection"
    GCS ─ "command" ─▶ GcsClient ─▶ CommandHandler ─▶ MAVLink ─▶ PX4

Nothing blocks anything: each subsystem runs on its own thread and they hand off through
thread-safe calls (get_state / submit_message). The telemetry cadence is a fixed 1 Hz timer
inside the WS client, independent of vision FPS.
"""

from __future__ import annotations

import logging
import signal
import threading
import time

from .config import Config, load_config
from .mavlink_bridge import MavlinkBridge
from .gcs_client import GcsClient
from .commands import CommandHandler
from .pipeline import VisionPipeline, VisionAlert
from .messages import build_telemetry, build_detection

logger = logging.getLogger("eqaab")


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


class EdgeNode:
    """Owns and supervises every subsystem on the Pi."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self._stop = threading.Event()

        # MAVLink telemetry/command bridge.
        self.bridge = MavlinkBridge(cfg.mavlink)

        # WebSocket client. Telemetry is pulled by its 1 Hz timer; commands are pushed to
        # the handler. Built before the handler so we can pass submit_message for feedback.
        self.client = GcsClient(
            cfg.gcs,
            build_telemetry=self._build_telemetry,
            on_command=self._on_command,
        )

        # Command handler (GCS → PX4), with event feedback back up the WS link.
        self.commands = CommandHandler(self.bridge, cfg, send_message=self.client.submit_message)

        # Vision pipeline; on each confirmed target, build a schema-exact detection and send.
        self.pipeline = VisionPipeline(cfg, on_alert=self._on_alert)

    # --- callbacks (called from other threads) ------------------------
    def _build_telemetry(self, latency_ms: int) -> dict:
        return build_telemetry(self.bridge.get_state(), latency_ms)

    def _on_alert(self, alert: VisionAlert) -> None:
        # Runs on the inference thread; enrich with the latest telemetry + geo, then enqueue.
        msg = build_detection(alert, self.bridge.get_state(), self.cfg)
        self.client.submit_detection(msg)
        logger.info("Detection sent: track=%d %s iff=%s conf=%.2f",
                    alert.track_id, alert.class_name, alert.iff_status, alert.confidence)

    def _on_command(self, msg: dict) -> None:
        self.commands.handle(msg)

    # --- lifecycle -----------------------------------------------------
    def start(self) -> None:
        logger.info("=" * 56)
        logger.info("  EQAAB edge node starting (drone_id=%s)", self.cfg.drone_id)
        logger.info("  GCS:     %s", self.cfg.gcs.ws_url)
        logger.info("  MAVLink: %s", self.cfg.mavlink.connection)
        logger.info("  Model:   %s (imgsz=%d, every %d frames)",
                    self.cfg.detector.model_path, self.cfg.detector.img_size,
                    self.cfg.detector.detect_every_n)
        logger.info("=" * 56)
        # Order: link first, then commands are ready, then start the heavy vision pipeline.
        self.bridge.start()
        self.client.start()
        self.pipeline.start()

    def run_forever(self) -> None:
        """Block the main thread until a signal arrives, logging periodic health."""
        signal.signal(signal.SIGINT, self._signal)
        signal.signal(signal.SIGTERM, self._signal)
        self.start()
        try:
            while not self._stop.is_set():
                self._stop.wait(5.0)
                if not self._stop.is_set():
                    logger.info("health | gcs=%s infer=%.1ffps cap=%.1ffps infer_ms=%.0f tracks=%d",
                                "up" if self.client.connected else "down",
                                self.pipeline.infer_fps, self.pipeline.capture_fps,
                                self.pipeline.last_infer_ms, len(self.pipeline.latest_tracks()))
        finally:
            self.stop()

    def _signal(self, *_args) -> None:
        logger.info("Shutdown signal received")
        self._stop.set()

    def stop(self) -> None:
        # Reverse order: stop producing vision, then the link, then the flight bridge.
        logger.info("Stopping edge node...")
        try:
            self.pipeline.stop()
        finally:
            try:
                self.client.stop()
            finally:
                self.bridge.stop()
        logger.info("Edge node stopped cleanly")


def main() -> int:
    cfg = load_config()
    _setup_logging(cfg.log_level)
    EdgeNode(cfg).run_forever()
    return 0
