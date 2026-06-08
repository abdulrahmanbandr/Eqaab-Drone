"""
One-shot helper: export a YOLOv8n `best.pt` to an NCNN model directory.

NCNN is the fastest practical backend for YOLOv8n on a Raspberry Pi 5 (no GPU, ARM
NEON optimised). Run this ONCE per trained model — ideally on your dev machine, then
copy the resulting `best_ncnn_model/` folder to the Pi (it's portable across archs).

Usage:
    python -m eqaab_edge.export_ncnn path/to/best.pt            # imgsz from .env (or 320)
    python -m eqaab_edge.export_ncnn path/to/best.pt --imgsz 416

Output:
    path/to/best_ncnn_model/      <- point MODEL_PATH at this directory

This is the only place we touch the .pt; at runtime the detector loads the NCNN dir.
"""

from __future__ import annotations

import argparse
import sys

from .config import load_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export YOLOv8n best.pt -> NCNN model dir")
    parser.add_argument("weights", help="Path to the trained PyTorch weights (e.g. best.pt)")
    parser.add_argument(
        "--imgsz",
        type=int,
        default=None,
        help="Square inference size (default: IMG_SIZE from config, typically 320).",
    )
    args = parser.parse_args(argv)

    imgsz = args.imgsz if args.imgsz is not None else load_config().detector.img_size
    if imgsz >= 640:
        print(f"[warn] imgsz={imgsz} is large for a Pi 5; 320 or 416 is recommended.")

    # Imported here so the export tool's heavy deps aren't pulled in at runtime.
    from ultralytics import YOLO

    print(f"[export] loading {args.weights} ...")
    model = YOLO(args.weights, task="detect")
    print(f"[export] exporting to NCNN at imgsz={imgsz} ...")
    out = model.export(format="ncnn", imgsz=imgsz)
    print(f"[export] done -> {out}")
    print("[export] set MODEL_PATH in your .env to this directory.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
