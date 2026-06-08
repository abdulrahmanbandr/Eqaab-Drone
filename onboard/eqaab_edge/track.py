"""
Module 3 — Tracking (DeepSort, stable track_ids).

Turns per-frame Detections into persistent tracks with stable integer `track_id`s — the
id the GCS alert schema needs (`track_id`). DeepSort fuses a Kalman motion model with an
appearance embedding, so an object keeps the same id across frames, brief occlusions, and
the gaps where we DON'T run detection (detect-every-N coasting).

How coasting works
------------------
The pipeline runs the detector only every Nth frame. On the in-between frames we still call
`update([], frame)` with no detections, and DeepSort's Kalman filter predicts each track
forward. Tracks survive up to `max_age` missed updates before being deleted. This is the
core lightweight trick: cheap motion prediction between expensive inference passes.

The wrapper returns plain `Track` dataclasses so nothing downstream imports DeepSort types.

Pi note
-------
The appearance embedder ("mobilenet" by default) runs on CPU via torch. It's the heaviest
tracking cost on a Pi 5; if you need more FPS, raise DETECT_EVERY_N (fewer embed calls) or
switch embedders via TRACK_EMBEDDER.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from .config import TrackerConfig
from .detect import Detection

logger = logging.getLogger(__name__)


@dataclass
class Track:
    """A confirmed/tentative tracked object with a stable id."""
    track_id: int                      # stable across frames — maps to schema `track_id`
    bbox: Tuple[int, int, int, int]    # x1, y1, x2, y2 (current, possibly Kalman-predicted)
    class_id: int                      # 0=drone, 1=person, 2=car
    class_name: str
    confidence: float                  # last associated detection confidence (0 while coasting)
    is_confirmed: bool                 # DeepSort considers it a real, stable track
    hits: int                          # total detections associated over its lifetime
    time_since_update: int             # frames since last real detection (0 = fresh, >0 = coasting)

    def is_alertable(self, confirm_hits: int) -> bool:
        """True once the track is confirmed, currently visible, and well-established."""
        return self.is_confirmed and self.time_since_update == 0 and self.hits >= confirm_hits


class Tracker:
    """Thin DeepSort wrapper producing stable `Track`s from `Detection`s."""

    def __init__(self, cfg: TrackerConfig, class_names: List[str]) -> None:
        self.cfg = cfg
        self._class_names = class_names
        self._name_to_id = {name: i for i, name in enumerate(class_names)}
        self._tracker = None
        # Last known confidence per track_id, so coasting frames report a sensible value
        # instead of None/0 flicker.
        self._last_conf: Dict[int, float] = {}

    def load(self) -> None:
        """Construct DeepSort. Heavy imports (torch via the embedder) happen here."""
        if self._tracker is not None:
            return
        from deep_sort_realtime.deepsort_tracker import DeepSort

        logger.info("Loading DeepSort [embedder=%s, gpu=%s, max_age=%d, n_init=%d]",
                    self.cfg.embedder, self.cfg.embedder_gpu, self.cfg.max_age, self.cfg.n_init)
        self._tracker = DeepSort(
            max_age=self.cfg.max_age,
            n_init=self.cfg.n_init,
            max_cosine_distance=self.cfg.max_cosine_distance,
            embedder=self.cfg.embedder,
            embedder_gpu=self.cfg.embedder_gpu,
            half=False,        # CPU on the Pi — no fp16
            bgr=True,          # our frames are BGR (OpenCV / picamera2-converted)
        )

    def update(self, detections: List[Detection], frame: np.ndarray) -> List[Track]:
        """Advance the tracker by one frame.

        Pass `detections=[]` on frames where the detector was skipped — DeepSort will
        coast existing tracks forward with its Kalman filter.
        """
        if self._tracker is None:
            raise RuntimeError("Tracker.load() must be called before update()")

        # DeepSort input format: ([left, top, w, h], confidence, class_name)
        raw = [(list(d.ltwh), d.confidence, d.class_name) for d in detections]
        ds_tracks = self._tracker.update_tracks(raw, frame=frame)

        out: List[Track] = []
        live_ids = set()
        for t in ds_tracks:
            tid = int(t.track_id)
            live_ids.add(tid)

            l, top, r, b = t.to_ltrb()
            class_name = t.get_det_class() or "unknown"
            class_id = self._name_to_id.get(class_name, -1)

            # det_conf is None on coasting frames; fall back to the last known value.
            conf = t.det_conf
            if conf is None:
                conf = self._last_conf.get(tid, 0.0)
            else:
                conf = float(conf)
                self._last_conf[tid] = conf

            out.append(
                Track(
                    track_id=tid,
                    bbox=(int(l), int(top), int(r), int(b)),
                    class_id=class_id,
                    class_name=class_name,
                    confidence=conf,
                    is_confirmed=t.is_confirmed(),
                    hits=int(getattr(t, "hits", 0)),
                    time_since_update=int(getattr(t, "time_since_update", 0)),
                )
            )

        # Forget confidences for tracks DeepSort has dropped, so the dict can't grow forever.
        for dead in set(self._last_conf) - live_ids:
            self._last_conf.pop(dead, None)

        return out
