from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def record_session_items_added(_session_id: str, _count: int) -> None:
    """Best-effort session metrics hook (no-op by default)."""
    return None


def record_session_length(_session_id: str, _length: int) -> None:
    """Best-effort session size gauge hook (no-op by default)."""
    return None


class PseudoSession:
    """In-memory session with optional TTL and max_items trimming."""

    def __init__(self, session_id: str, ttl_seconds: Optional[int] = None, max_items: Optional[int] = None):
        self.session_id = session_id
        self._items: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._ttl = ttl_seconds
        self._max_items = max_items

    async def get_items(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        async with self._lock:
            items = list(self._items)

        if self._ttl is not None:
            cutoff = datetime.now(timezone.utc).timestamp() - self._ttl
            items = [
                it
                for it in items
                if float(it.get("ts", datetime.now(timezone.utc).timestamp())) >= cutoff
            ]

        if limit is not None:
            items = items[-limit:]
        return items

    async def add_items(self, items: List[Dict[str, Any]]) -> None:
        async with self._lock:
            self._items.extend(items)
            if self._max_items is not None and len(self._items) > self._max_items:
                self._items = self._items[-self._max_items :]

    async def pop_item(self) -> Optional[Dict[str, Any]]:
        async with self._lock:
            if not self._items:
                return None
            item = self._items.pop()

        try:
            current_len = len(await self.get_items())
            record_session_length(self.session_id, current_len)
        except Exception:
            logger.debug("Failed to update session length metric after pop", exc_info=True)
        return item

    async def clear_session(self) -> None:
        async with self._lock:
            self._items.clear()
        record_session_length(self.session_id, 0)
