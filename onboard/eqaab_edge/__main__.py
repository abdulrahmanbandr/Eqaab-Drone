"""Entrypoint: `python -m eqaab_edge` boots the full edge node."""

from __future__ import annotations

import sys

from .app import main

if __name__ == "__main__":
    sys.exit(main())
