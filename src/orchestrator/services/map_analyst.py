"""MapAnalyst: fetches map image + metadata from Mission Control.

Provides raw map data (PNG bytes + metadata) to the MapAnalyst agent,
which analyzes it in context of the specific navigation task via vision LLM.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


@dataclass
class MapContext:
    image_bytes: bytes
    metadata: dict = field(default_factory=dict)


async def get_map_context() -> MapContext | None:
    """Fetch map PNG + metadata from Mission Control.

    Returns None if map is unavailable (non-fatal — plan continues without map context).
    """
    base_url = os.getenv("MISSION_CONTROL_URL", "http://localhost:8050").rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            meta_resp = await http.get(f"{base_url}/api/v1/map/metadata")
            meta_resp.raise_for_status()
            metadata: dict = meta_resp.json()

            img_resp = await http.get(f"{base_url}/api/v1/map")
            img_resp.raise_for_status()
            image_bytes = img_resp.content
    except Exception:
        logger.exception("Failed to fetch map from Mission Control at %s", base_url)
        return None

    if not image_bytes:
        logger.warning("Mission Control returned empty map image")
        return None

    # Inject image dimensions into metadata if the API didn't provide them.
    # PNG header: bytes 16-24 contain width and height as big-endian uint32.
    if "width" not in metadata and "height" not in metadata and len(image_bytes) >= 24:
        import struct
        try:
            if image_bytes[:4] == b"\x89PNG":
                w = struct.unpack(">I", image_bytes[16:20])[0]
                h = struct.unpack(">I", image_bytes[20:24])[0]
                metadata = {**metadata, "width": w, "height": h}
        except Exception:
            pass

    return MapContext(image_bytes=image_bytes, metadata=metadata)


__all__ = ["MapContext", "get_map_context"]
