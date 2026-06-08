"""
Module 4 (wiring) — Vision pipeline: capture → detect → track → IFF.

Ties the vision modules together on a DEDICATED inference thread, fully decoupled from
camera capture (its own thread, in capture.py) and from the MAVLink/WebSocket I/O (their
own threads, added later). Nothing here blocks the network or telemetry timers.

Per-frame flow on the inference thread
--------------------------------------
    latest = capture.wait_frame()                 # newest frame only (no backlog)
    run_det = (frame_idx % DETECT_EVERY_N == 0)
    dets    = detector.infer(latest) if run_det else []   # heavy pass only every Nth frame
    tracks  = tracker.update(dets, latest)        # DeepSort coasts on the empty frames
    emit alerts for newly-confirmed tracks (classified via the IFF policy)

The detect-every-N + coast pattern is the main lightweight lever: YOLO runs at FPS/N while
track ids stay stable every frame via the Kalman filter.

Alerting
--------
The GCS schema wants an alert "immediately on a confirmed tracked target". We fire the
`on_alert` callback ONCE per track id, the first time it becomes alertable (confirmed +
visible + enough hits). Geo-projection (target lat/lon) and the wire timestamp are added
later by the message builder, which has the live telemetry; the pipeline stays vision-only.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from .config import Config
from .capture import create_capture
from .detect import Detector
from .track import Tracker, Track
from .iff import classify_iff

logger = logging.getLogger(__name__)


@dataclass
class VisionAlert:
    """A confirmed target handed off to the network layer (pre geo-projection)."""
    track_id: int
    class_id: int
    class_name: str
    confidence: float
    iff_status: str                     # "friendly" | "unknown" | "hostile"
    bbox: Tuple[int, int, int, int]     # x1, y1, x2, y2 in frame pixels
    frame_w: int                        # frame size, so the geo step can use bbox center
    frame_h: int


class VisionPipeline:
    """Threaded capture→detect→track→IFF producer of tracks and alerts."""

    def __init__(self, cfg: Config, on_alert: Optional[Callable[[VisionAlert], None]] = None) -> None:
        self.cfg = cfg
        self._on_alert = on_alert

        self._capture = create_capture(cfg.camera)
        self._detector = Detector(cfg.detector)
        self._tracker = Tracker(cfg.tracker, cfg.detector.class_names)

        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()

        # Shared state (single-writer = inference thread; readers take the lock).
        self._lock = threading.Lock()
        self._latest_tracks: List[Track] = []
        self._alerted_ids: set[int] = set()

        # Metrics.
        self._infer_fps = 0.0
        self._frames_since_tick = 0
        self._last_tick = time.monotonic()

    # --- lifecycle -----------------------------------------------------
    def start(self) -> None:
        if self._thread is not None:
            return
        # Load heavy models BEFORE starting the camera so warm-up cost isn't on the hot path.
        self._detector.load()
        self._tracker.load()
        self._capture.start()
        self._running.set()
        self._thread = threading.Thread(target=self._loop, name="vision-infer", daemon=True)
        self._thread.start()
        logger.info("Vision pipeline started (detect every %d frames, imgsz=%d, backend=%s)",
                    self.cfg.detector.detect_every_n, self.cfg.detector.img_size, self._detector.backend)

    def stop(self) -> None:
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        self._capture.stop()
        logger.info("Vision pipeline stopped")

    # --- inference thread ---------------------------------------------
    def _loop(self) -> None:
        n = max(1, self.cfg.detector.detect_every_n)
        frame_idx = 0
        while self._running.is_set():
            frame = self._capture.wait_frame(timeout=1.0)
            if frame is None:
                continue  # no frame yet (camera warming up or stalled)

            try:
                run_det = (frame_idx % n == 0)
                detections = self._detector.infer(frame) if run_det else []
                tracks = self._tracker.update(detections, frame)
            except Exception:
                logger.exception("Inference/tracking step failed; skipping frame")
                continue

            with self._lock:
                self._latest_tracks = tracks
            self._maybe_alert(tracks, frame.shape[1], frame.shape[0])

            frame_idx += 1
            self._meter()

    def _maybe_alert(self, tracks: List[Track], frame_w: int, frame_h: int) -> None:
        if self._on_alert is None:
            return
        confirm_hits = self.cfg.tracker.confirm_hits
        for t in tracks:
            if t.track_id in self._alerted_ids:
                continue
            if not t.is_alertable(confirm_hits):
                continue
            status = classify_iff(t.class_name, t.confidence, self.cfg.iff)
            alert = VisionAlert(
                track_id=t.track_id,
                class_id=t.class_id,
                class_name=t.class_name,
                confidence=t.confidence,
                iff_status=status,
                bbox=t.bbox,
                frame_w=frame_w,
                frame_h=frame_h,
            )
            self._alerted_ids.add(t.track_id)
            try:
                self._on_alert(alert)
            except Exception:
                logger.exception("on_alert callback raised")

    def _meter(self) -> None:
        self._frames_since_tick += 1
        now = time.monotonic()
        dt = now - self._last_tick
        if dt >= 1.0:
            self._infer_fps = self._frames_since_tick / dt
            self._frames_since_tick = 0
            self._last_tick = now

    # --- readers -------------------------------------------------------
    def latest_tracks(self) -> List[Track]:
        with self._lock:
            return list(self._latest_tracks)

    @property
    def infer_fps(self) -> float:
        return self._infer_fps

    @property
    def capture_fps(self) -> float:
        return self._capture.measured_fps

    @property
    def last_infer_ms(self) -> float:
        return self._detector.last_infer_ms


# ──────────────────────────────────────────────────────────────────────
# Standalone demo: run the vision side only (no MAVLink, no WebSocket).
# Useful to validate the camera + model + tracker on the Pi before the
# network layers exist:   python -m eqaab_edge.pipeline
# ──────────────────────────────────────────────────────────────────────

def _demo() -> int:  # pragma: no cover - manual hardware test
    import signal
    from .config import load_config

    cfg = load_config()
    logging.basicConfig(
        level=getattr(logging, cfg.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    def on_alert(a: VisionAlert) -> None:
        logger.info("ALERT track=%d class=%s conf=%.2f iff=%s bbox=%s",
                    a.track_id, a.class_name, a.confidence, a.iff_status, list(a.bbox))

    pipe = VisionPipeline(cfg, on_alert=on_alert)

    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())

    pipe.start()
    logger.info("Vision demo running — Ctrl-C to stop")
    try:
        while not stop.is_set():
            stop.wait(2.0)
            logger.info("infer=%.1f fps  capture=%.1f fps  last_infer=%.0f ms  tracks=%d",
                        pipe.infer_fps, pipe.capture_fps, pipe.last_infer_ms,
                        len(pipe.latest_tracks()))
    finally:
        pipe.stop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_demo())
