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

    return MapContext(image_bytes=image_bytes, metadata=metadata)


__all__ = ["MapContext", "get_map_context"]
