"""
Module 1 — Camera capture (threaded, non-blocking).

A dedicated thread continuously grabs frames and keeps ONLY the most recent one in a
single-slot buffer. The inference thread reads the latest frame whenever it's ready;
slow inference therefore never stalls capture, and we never build a backlog of stale
frames (which would add latency on the Pi). This is the classic "drop to newest" pattern.

Two backends:
  * Picamera2  — Raspberry Pi Camera Module 3 (default, libcamera). Best on Pi 5.
  * OpenCV     — USB/UVC webcam via V4L2.

Both expose the same tiny interface:
    cap = create_capture(cfg)
    cap.start()
    frame = cap.read()          # latest BGR ndarray, or None if not ready yet
    fps = cap.measured_fps
    cap.stop()
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import numpy as np

from .config import CameraConfig

logger = logging.getLogger(__name__)


class _LatestFrame:
    """Thread-safe single-slot buffer holding only the newest frame."""

    def __init__(self) -> None:
        self._frame: Optional[np.ndarray] = None
        self._seq: int = 0
        self._lock = threading.Lock()
        self._event = threading.Event()

    def set(self, frame: np.ndarray) -> None:
        with self._lock:
            self._frame = frame
            self._seq += 1
        self._event.set()

    def get(self) -> Optional[np.ndarray]:
        with self._lock:
            return self._frame

    def get_with_seq(self) -> tuple[Optional[np.ndarray], int]:
        with self._lock:
            return self._frame, self._seq

    def wait(self, timeout: float) -> bool:
        """Block until at least one new frame has arrived since last clear."""
        got = self._event.wait(timeout)
        self._event.clear()
        return got


class BaseCapture:
    """Common threading/FPS-measurement scaffolding for both backends."""

    def __init__(self, cfg: CameraConfig) -> None:
        self.cfg = cfg
        self._buf = _LatestFrame()
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._fps = 0.0
        self._frames_since_tick = 0
        self._last_tick = time.monotonic()

    # --- backend hooks -------------------------------------------------
    def _open(self) -> None:  # pragma: no cover - hardware
        raise NotImplementedError

    def _grab(self) -> Optional[np.ndarray]:  # pragma: no cover - hardware
        raise NotImplementedError

    def _close(self) -> None:  # pragma: no cover - hardware
        raise NotImplementedError

    # --- lifecycle -----------------------------------------------------
    def start(self) -> None:
        if self._thread is not None:
            return
        self._open()
        self._running.set()
        self._thread = threading.Thread(target=self._loop, name="camera-capture", daemon=True)
        self._thread.start()
        logger.info("Camera capture started (%s, %dx%d @ %d fps target)",
                    self.cfg.source, self.cfg.width, self.cfg.height, self.cfg.fps)

    def _loop(self) -> None:
        while self._running.is_set():
            try:
                frame = self._grab()
            except Exception:
                logger.exception("Camera grab failed; retrying shortly")
                time.sleep(0.5)
                continue
            if frame is None:
                time.sleep(0.005)
                continue
            self._buf.set(frame)
            self._measure()

    def _measure(self) -> None:
        self._frames_since_tick += 1
        now = time.monotonic()
        dt = now - self._last_tick
        if dt >= 1.0:
            self._fps = self._frames_since_tick / dt
            self._frames_since_tick = 0
            self._last_tick = now

    def read(self) -> Optional[np.ndarray]:
        """Non-blocking: return the latest frame (or None if none yet)."""
        return self._buf.get()

    def read_with_seq(self) -> tuple[Optional[np.ndarray], int]:
        return self._buf.get_with_seq()

    def wait_frame(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """Block up to `timeout`s for a fresh frame, then return the latest."""
        self._buf.wait(timeout)
        return self._buf.get()

    @property
    def measured_fps(self) -> float:
        return self._fps

    def stop(self) -> None:
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        try:
            self._close()
        except Exception:
            logger.exception("Error while closing camera")
        logger.info("Camera capture stopped")


class Picamera2Capture(BaseCapture):
    """Raspberry Pi Camera Module 3 via picamera2 / libcamera."""

    def _open(self) -> None:  # pragma: no cover - hardware
        from picamera2 import Picamera2  # imported lazily; only present on the Pi
        from libcamera import Transform

        self._picam = Picamera2()
        video_cfg = self._picam.create_video_configuration(
            main={"size": (self.cfg.width, self.cfg.height), "format": "RGB888"},
            transform=Transform(hflip=int(self.cfg.hflip), vflip=int(self.cfg.vflip)),
            controls={"FrameRate": float(self.cfg.fps)},
        )
        self._picam.configure(video_cfg)
        self._picam.start()
        # Give the sensor a moment to settle (AE/AWB) before the first read.
        time.sleep(0.5)

    def _grab(self) -> Optional[np.ndarray]:  # pragma: no cover - hardware
        # picamera2 returns RGB; the rest of the pipeline (OpenCV/YOLO) expects BGR.
        import cv2

        rgb = self._picam.capture_array()
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    def _close(self) -> None:  # pragma: no cover - hardware
        if getattr(self, "_picam", None) is not None:
            self._picam.stop()
            self._picam.close()
            self._picam = None


class OpenCVCapture(BaseCapture):
    """USB/UVC webcam via OpenCV V4L2 (fallback backend)."""

    def _open(self) -> None:  # pragma: no cover - hardware
        import cv2

        self._cap = cv2.VideoCapture(self.cfg.device_index, cv2.CAP_V4L2)
        # MJPG keeps USB bandwidth sane at higher resolutions on the Pi.
        self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cfg.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cfg.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.cfg.fps)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # minimize driver-side latency
        if not self._cap.isOpened():
            raise RuntimeError(f"Could not open USB camera index {self.cfg.device_index}")

    def _grab(self) -> Optional[np.ndarray]:  # pragma: no cover - hardware
        ok, frame = self._cap.read()
        if not ok:
            return None
        return frame

    def _close(self) -> None:  # pragma: no cover - hardware
        if getattr(self, "_cap", None) is not None:
            self._cap.release()
            self._cap = None


def create_capture(cfg: CameraConfig) -> BaseCapture:
    """Factory: pick the capture backend from config."""
    source = cfg.source.strip().lower()
    if source == "picamera2":
        return Picamera2Capture(cfg)
    if source == "opencv":
        return OpenCVCapture(cfg)
    raise ValueError(f"Unknown CAMERA_SOURCE '{cfg.source}' (expected 'picamera2' or 'opencv')")
