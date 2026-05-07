"""Annotate an occupancy-grid map image with robot position markers.

Converts real-world robot poses (metres) to pixel coordinates using map
metadata (resolution + origin offsets), then draws coloured circles and
labels so vision-LLM agents can see where each robot is on the map.
"""

from __future__ import annotations

import io
import logging
import math
import os
from dataclasses import dataclass
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

# Colour palette per robot state — (R, G, B)
_STATE_COLOURS = {
    "IDLE":           (0,   200,  60),   # green
    "ON_TASK":        (0,   120, 255),   # blue
    "CHARGING":       (255, 190,   0),   # yellow
    "MAP_DEPLOYMENT": (180,   0, 255),   # purple
    "TELEOP":         (255, 100,   0),   # orange
}
_OFFLINE_COLOUR  = (180,  30,  30)       # dark red
_DEFAULT_COLOUR  = (140, 140, 140)       # grey


@dataclass
class RobotMarker:
    name: str
    x: float           # real-world metres
    y: float           # real-world metres
    state: str         # e.g. "IDLE", "ON_TASK"
    battery: float     # 0-100
    online: bool


async def fetch_robot_markers() -> List[RobotMarker]:
    """Pull robot positions from Mission Dispatch REST API.

    Returns an empty list if the service is unreachable (non-fatal).
    """
    base_url = os.getenv("MISSION_DISPATCH_URL", "http://localhost:5002").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            resp = await http.get(f"{base_url}/robot")
            resp.raise_for_status()
            robots = resp.json()
    except Exception:
        logger.warning("Could not fetch robots for map overlay (non-fatal)")
        return []

    markers: List[RobotMarker] = []
    for r in robots if isinstance(robots, list) else []:
        status = r.get("status", {})
        pose = status.get("pose") or {}
        x = pose.get("x")
        y = pose.get("y")
        if x is None or y is None:
            continue
        markers.append(
            RobotMarker(
                name=r.get("name", "?"),
                x=float(x),
                y=float(y),
                state=status.get("state", "UNKNOWN"),
                battery=float(status.get("battery_level") or 0),
                online=bool(status.get("online", False)),
            )
        )
    return markers


def annotate_map(
    image_bytes: bytes,
    metadata: dict,
    robots: List[RobotMarker],
    *,
    marker_radius: int = 8,
    font_size: int = 14,
) -> bytes:
    """Draw robot markers onto the occupancy map PNG.

    Each robot gets a coloured filled circle + a label: «name (state %)».
    Coordinate conversion: pixel = (real − origin) / resolution.
    Y-axis is flipped because PNG rows go top→bottom while map Y goes bottom→up.

    Returns the annotated PNG bytes, or the original bytes on any error.
    """
    if not robots:
        return image_bytes

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning("Pillow not installed — skipping robot overlay on map")
        return image_bytes

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        draw = ImageDraw.Draw(img)

        resolution: float = float(metadata.get("resolution") or 0.05)
        x_offset: float  = float(metadata.get("x_offset")   or 0.0)
        y_offset: float  = float(metadata.get("y_offset")    or 0.0)
        height: int      = img.height

        # Try to load a reasonably sized font; fall back to PIL default.
        font: Optional[object] = None
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            try:
                font = ImageFont.load_default(size=font_size)
            except Exception:
                font = ImageFont.load_default()

        for robot in robots:
            px = int((robot.x - x_offset) / resolution)
            # Flip Y: map Y increases upward, image Y increases downward
            py = int(height - (robot.y - y_offset) / resolution)

            if robot.online:
                colour = _STATE_COLOURS.get(robot.state, _DEFAULT_COLOUR)
            else:
                colour = _OFFLINE_COLOUR

            r = marker_radius
            # Filled circle
            draw.ellipse([(px - r, py - r), (px + r, py + r)], fill=colour)
            # White border for contrast
            draw.ellipse([(px - r, py - r), (px + r, py + r)], outline=(255, 255, 255), width=2)
            # Cross-hair dot in the centre
            draw.ellipse([(px - 2, py - 2), (px + 2, py + 2)], fill=(255, 255, 255))

            label = f"{robot.name} ({robot.state[:4]} {robot.battery:.0f}%)"
            draw.text((px + r + 3, py - font_size // 2), label, fill=(255, 255, 0), font=font)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    except Exception:
        logger.exception("Failed to annotate map with robot markers")
        return image_bytes


def robots_to_text(robots: List[RobotMarker]) -> str:
    """Format robot list as a compact text block for the LLM prompt."""
    if not robots:
        return "(no robot position data available)"
    lines = []
    for r in robots:
        status_str = "OFFLINE" if not r.online else r.state
        lines.append(
            f"  • {r.name}: pos=({r.x:.2f}, {r.y:.2f})m  state={status_str}"
            f"  battery={r.battery:.0f}%"
        )
    return "\n".join(lines)


__all__ = ["RobotMarker", "fetch_robot_markers", "annotate_map", "robots_to_text"]
