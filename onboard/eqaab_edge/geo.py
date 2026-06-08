"""
Module 5 (math) — Target geo-projection.

Given where a target sits in the image, plus the drone's pose and the camera geometry,
estimate the target's ground latitude/longitude. This fills the alert's `target_lat` /
`target_lon` fields.

It is a deliberately LIGHTWEIGHT, flat-earth, pinhole approximation:
  * model the pixel as a ray leaving the camera,
  * point that ray using the camera azimuth (where it faces) and depression (how far below
    horizontal it looks),
  * intersect the ray with flat ground `agl_m` metres below the drone,
  * convert the local East/North offset to a lat/lon delta.

Assumptions / limits (documented on purpose):
  * Flat ground at the drone's launch level; no terrain/DEM. Good for short ranges.
  * Zero camera roll; small-angle coupling between pixel offset and world angle is ignored
    (fine for the Pi Cam Module 3's modest FOV, not for fisheye).
  * `agl_m` is height above the ground plane the target stands on (use relative altitude).
All trig is stdlib `math` — no numpy, nothing heavy.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

from .config import GeoConfig

# Metres per degree of latitude (WGS-84 mean). Longitude scales by cos(latitude).
_M_PER_DEG_LAT = 111_320.0


def resolve_camera_orientation(
    heading_deg: float,
    geo_cfg: GeoConfig,
    gimbal_depression_deg: Optional[float] = None,
    gimbal_yaw_deg: Optional[float] = None,
) -> Tuple[float, float]:
    """Work out the optical axis azimuth (deg from North, CW) and depression (deg below
    horizontal) from the drone heading, the config mount, and optional live gimbal data.

    gimbal_depression_deg : depression below horizontal, positive = looking down (optional).
    gimbal_yaw_deg        : yaw relative to the drone nose, + = right (optional).
    """
    use_gimbal = geo_cfg.use_mavlink_gimbal
    depression = (
        gimbal_depression_deg
        if (use_gimbal and gimbal_depression_deg is not None)
        else geo_cfg.mount_pitch_down_deg
    )
    rel_yaw = (
        gimbal_yaw_deg
        if (use_gimbal and gimbal_yaw_deg is not None)
        else geo_cfg.mount_yaw_deg
    )
    azimuth = (heading_deg + rel_yaw) % 360.0
    return azimuth, depression


def project_target(
    bbox: Tuple[int, int, int, int],
    frame_w: int,
    frame_h: int,
    drone_lat: float,
    drone_lon: float,
    agl_m: float,
    cam_azimuth_deg: float,
    cam_depression_deg: float,
    hfov_deg: float,
    vfov_deg: float,
) -> Optional[Tuple[float, float]]:
    """Estimate target (lat, lon) from its bbox. Returns None if it can't hit the ground
    (camera not looking down, or drone effectively on the ground)."""
    if agl_m <= 0.0:
        return None

    x1, y1, x2, y2 = bbox
    u = (x1 + x2) / 2.0          # bbox horizontal centre
    v = (y1 + y2) / 2.0          # bbox vertical centre
    cx, cy = frame_w / 2.0, frame_h / 2.0

    # Pinhole focal lengths in pixels from the FOVs.
    fx = cx / math.tan(math.radians(hfov_deg) / 2.0)
    fy = cy / math.tan(math.radians(vfov_deg) / 2.0)

    # Per-pixel angular offsets from the optical axis.
    alpha = math.atan2(u - cx, fx)     # horizontal, + = right of centre
    beta = math.atan2(v - cy, fy)      # vertical,   + = below centre (further down)

    # Ray azimuth/elevation (small-angle approximation, zero roll).
    azimuth = math.radians(cam_azimuth_deg) + alpha
    elevation = -math.radians(cam_depression_deg) - beta   # negative = below horizon

    sin_el = math.sin(elevation)
    if sin_el >= 0.0:
        # Ray points at or above the horizon — never reaches the ground.
        return None

    # Ground intersection: descend agl_m along the ray's downward component.
    t = agl_m / (-sin_el)              # slant range to ground
    cos_el = math.cos(elevation)
    east = t * cos_el * math.sin(azimuth)
    north = t * cos_el * math.cos(azimuth)

    dlat = north / _M_PER_DEG_LAT
    dlon = east / (_M_PER_DEG_LAT * math.cos(math.radians(drone_lat)))
    return drone_lat + dlat, drone_lon + dlon
