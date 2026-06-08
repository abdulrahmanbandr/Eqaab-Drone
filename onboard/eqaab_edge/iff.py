"""
Module 4 — IFF (Identify Friend or Foe) policy.

This is the ONE place the friend/foe decision lives. Everything about the policy is in the
single pure function `classify_iff()` below — no I/O, no globals, no side effects — so it's
trivial to read, unit-test, and tune. Change the rules here and nowhere else.

Output contract
---------------
Returns one of the three strings below, which match `backend/models/schemas.py`'s
`IFFStatus` enum EXACTLY (lowercase). The message builder serializes the result verbatim
into the alert's `iff_status` field — do not transform it elsewhere.

    IFF_FRIENDLY = "friendly"
    IFF_UNKNOWN  = "unknown"
    IFF_HOSTILE  = "hostile"

Vision-only caveat (important, by design)
-----------------------------------------
Eqaab's IFF is camera-only — there is no radar or transponder. A camera CANNOT read a
drone's identity from pixels, so it can never *prove* "friendly" on its own. The
`friendly_drone_ids` allowlist is therefore matched against an OPTIONAL external identity
hint (`identity`) that a future Remote ID / MAVLink / ADS-B source may supply. When no such
identity is available (the current vision-only path), nothing is classified "friendly", and
the decision falls back to a class+confidence threat rule. This keeps the function honest:
it never invents a friendly it cannot verify.
"""

from __future__ import annotations

from typing import Optional

from .config import IffConfig

# Canonical IFF result strings — must equal schemas.py IFFStatus values.
IFF_FRIENDLY = "friendly"
IFF_UNKNOWN = "unknown"
IFF_HOSTILE = "hostile"

# Classes that represent a potential threat in a secured airspace/perimeter:
#   drone  — unauthorized aircraft
#   person — human intruder
#   car    — unauthorized vehicle
# (All three of the unified model's classes are threat-relevant in this deployment.)
THREAT_CLASSES = frozenset({"drone", "person", "car"})


def classify_iff(
    class_name: str,
    confidence: float,
    cfg: IffConfig,
    identity: Optional[str] = None,
) -> str:
    """Decide friend/foe for one tracked target. Pure function — tune freely.

    Parameters
    ----------
    class_name : detector class ("drone" | "person" | "car").
    confidence : last detection confidence for the track, 0.0–1.0.
    cfg        : IffConfig (friendly allowlist + hostile confidence threshold).
    identity   : OPTIONAL verified identifier from a non-vision source (Remote ID /
                 MAVLink / ADS-B). None on the vision-only path. Only a positive match
                 here can ever yield "friendly".

    Returns one of IFF_FRIENDLY / IFF_UNKNOWN / IFF_HOSTILE.
    """
    # ── Rule 1: verified friendly (requires an external identity we trust) ──────────
    # Case-insensitive allowlist match. Vision alone supplies no identity, so in the
    # current build this branch only fires once a Remote ID/MAVLink source is wired in.
    if identity:
        allow = {x.strip().upper() for x in cfg.friendly_drone_ids}
        if identity.strip().upper() in allow:
            return IFF_FRIENDLY

    # ── Rule 2: threat by class + confidence ────────────────────────────────────────
    # A confident detection of a threat-relevant class with no friendly identity is
    # treated as hostile; a low-confidence one stays "unknown" pending more evidence.
    if class_name in THREAT_CLASSES:
        if confidence >= cfg.hostile_min_confidence:
            return IFF_HOSTILE
        return IFF_UNKNOWN

    # ── Rule 3: anything else is unknown ────────────────────────────────────────────
    return IFF_UNKNOWN
