"""
Module 2 — Detection (single unified YOLOv8n, one inference pass).

Wraps Ultralytics YOLO behind a tiny, dependency-light interface. The model is the
ONE custom model `best.pt` (classes: drone=0, person=1, car=2) — never two sequential
models. We run a single forward pass per detected frame and return plain dataclasses,
so the rest of the pipeline never imports torch/ultralytics types.

Backend preference (fastest → slowest on a Pi 5):
    1. NCNN   — a "<name>_ncnn_model" directory   (PREFERRED on Raspberry Pi)
    2. ONNX   — a "<name>.onnx" file
    3. PyTorch— the raw "best.pt"                  (fallback only; slowest)

The backend is chosen purely from MODEL_PATH (config), so swapping it is a .env change.
To create the NCNN export from best.pt, run:  python -m eqaab_edge.export_ncnn best.pt

Lightweight notes
-----------------
* imgsz is 320/416 (never 640) — set in config.
* Inference is CPU-only on the Pi; we don't import or probe CUDA.
* This class is synchronous and thread-safe to *call from one* inference thread; the
  threaded capture→infer→track wiring lives in the pipeline module (next step).
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from .config import DetectorConfig

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """One detected object in a single frame (pre-tracking)."""
    bbox: Tuple[int, int, int, int]   # x1, y1, x2, y2 in pixel coords of the input frame
    confidence: float                 # 0.0 – 1.0
    class_id: int                     # 0=drone, 1=person, 2=car
    class_name: str                   # resolved via config.class_names

    @property
    def ltwh(self) -> Tuple[int, int, int, int]:
        """left, top, width, height — the format DeepSort wants as input."""
        x1, y1, x2, y2 = self.bbox
        return x1, y1, x2 - x1, y2 - y1


def _resolve_backend(model_path: str) -> str:
    """Human-readable backend label from the path (for logging only)."""
    p = model_path.rstrip("/")
    if p.endswith("_ncnn_model") or os.path.isdir(p):
        return "NCNN"
    if p.endswith(".onnx"):
        return "ONNX"
    if p.endswith(".pt"):
        return "PyTorch (.pt — slow on Pi; prefer an NCNN export)"
    return "unknown"


class Detector:
    """Unified YOLOv8n detector. One model, one pass per frame."""

    def __init__(self, cfg: DetectorConfig) -> None:
        self.cfg = cfg
        self._model = None
        self._backend = _resolve_backend(cfg.model_path)
        self.last_infer_ms: float = 0.0

    # --- lifecycle -----------------------------------------------------
    def load(self) -> None:
        """Load the model. Heavy imports happen here, not at module import time."""
        if self._model is not None:
            return
        if not os.path.exists(self.cfg.model_path):
            raise FileNotFoundError(
                f"MODEL_PATH '{self.cfg.model_path}' not found. Put best.pt / best.onnx / "
                f"a *_ncnn_model dir there, or export one:\n"
                f"    python -m eqaab_edge.export_ncnn path/to/best.pt"
            )
        # Imported lazily so unit tests / non-Pi tooling don't pay the cost.
        from ultralytics import YOLO

        logger.info("Loading detector: %s  [backend=%s, imgsz=%d]",
                    self.cfg.model_path, self._backend, self.cfg.img_size)
        # task='detect' avoids Ultralytics auto-probing the task on every load.
        self._model = YOLO(self.cfg.model_path, task="detect")
        # Warm up once so the first real frame isn't penalised by lazy graph init.
        try:
            dummy = np.zeros((self.cfg.img_size, self.cfg.img_size, 3), dtype=np.uint8)
            self._model.predict(dummy, imgsz=self.cfg.img_size, verbose=False)
            logger.info("Detector warm-up complete")
        except Exception:  # pragma: no cover - warm-up is best-effort
            logger.warning("Detector warm-up failed (continuing)", exc_info=True)

    # --- inference -----------------------------------------------------
    def infer(self, frame: np.ndarray) -> List[Detection]:
        """Run ONE forward pass on a BGR frame and return filtered detections."""
        if self._model is None:
            raise RuntimeError("Detector.load() must be called before infer()")

        t0 = time.monotonic()
        results = self._model.predict(
            frame,
            imgsz=self.cfg.img_size,
            conf=self.cfg.conf_threshold,
            iou=self.cfg.iou_threshold,
            verbose=False,
        )
        self.last_infer_ms = (time.monotonic() - t0) * 1000.0

        detections: List[Detection] = []
        if not results:
            return detections

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return detections

        # Pull tensors to CPU/numpy once (cheaper than per-row .item() calls).
        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        clss = boxes.cls.cpu().numpy().astype(int)
        n_classes = len(self.cfg.class_names)

        for (x1, y1, x2, y2), conf, cid in zip(xyxy, confs, clss):
            if cid < 0 or cid >= n_classes:
                # Detection from an unexpected class id — skip rather than crash.
                continue
            detections.append(
                Detection(
                    bbox=(int(x1), int(y1), int(x2), int(y2)),
                    confidence=float(conf),
                    class_id=int(cid),
                    class_name=self.cfg.class_names[cid],
                )
            )
        return detections

    @property
    def backend(self) -> str:
        return self._backend
