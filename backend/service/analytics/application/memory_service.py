"""Memory service facade used by agent/chat pipelines.

This service keeps backward compatibility for existing imports while delegating
actual provider calls to `service.services.agents.integration` layer.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from service.services.agents.integration import BaseMemoryIntegration, get_memory_integration

logger = logging.getLogger(__name__)


class MemoryService:
    """Facade for memory operations used by agent layer and background tasks."""

    def __init__(self, integration: BaseMemoryIntegration | None = None) -> None:
        self.integration = integration or get_memory_integration()

    @staticmethod
    def _memory_user_scope(user_id: str) -> str:
        normalized = str(user_id or "").strip()
        if not normalized:
            return ""
        # Use explicit user-level namespace so memory is shared across all threads.
        return f"user:{normalized}"

    async def get_memory_context(self, user_id: str, top_k: int = 5) -> str:
        if not user_id:
            return ""
        scoped_user_id = self._memory_user_scope(str(user_id))
        if not scoped_user_id:
            return ""
        try:
            context = await self.integration.get_memory_context(user_id=scoped_user_id, top_k=top_k)
            if context:
                return context
            # Backward-compatibility with previously stored raw user_id memories.
            return await self.integration.get_memory_context(user_id=str(user_id), top_k=top_k)
        except Exception:
            logger.debug("Memory context loading failed", exc_info=True)
            return ""

    async def extract_and_save_facts(
        self,
        user_id: str,
        thread_id: str,
        messages: list[dict[str, Any]],
    ) -> None:
        if not user_id or not messages:
            return

        scoped_user_id = self._memory_user_scope(str(user_id))
        if not scoped_user_id:
            return

        metadata = {
            "thread_id": str(thread_id),
            "source": "gpthub-agent",
            "user_scope": scoped_user_id,
        }
        try:
            await self.integration.save_messages(
                user_id=scoped_user_id,
                messages=messages,
                metadata=metadata,
            )
        except Exception:
            logger.debug("Memory extraction/save failed", exc_info=True)

    @staticmethod
    def _normalize_datetime(value: Any) -> str | None:
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.isoformat()
        return None

    @staticmethod
    def _normalize_fact_item(item: dict[str, Any], index: int) -> dict[str, Any] | None:
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}

        fact_value = item.get("memory") or item.get("text") or item.get("content") or metadata.get("fact_value")
        if not isinstance(fact_value, str) or not fact_value.strip():
            return None
        fact_value = fact_value.strip()

        fact_key = metadata.get("fact_key")
        if not isinstance(fact_key, str) or not fact_key.strip():
            if ":" in fact_value:
                left, right = fact_value.split(":", 1)
                candidate = left.strip()
                if candidate:
                    fact_key = candidate
                    fact_value = right.strip() or fact_value
            if not isinstance(fact_key, str) or not fact_key.strip():
                fact_key = fact_value[:80]

        fact_type = metadata.get("fact_type")
        if not isinstance(fact_type, str) or not fact_type.strip():
            fact_type = "general"

        fact_id = (
            item.get("id")
            or item.get("memory_id")
            or item.get("_id")
            or metadata.get("id")
            or f"fact-{index}"
        )

        confidence = item.get("score") or item.get("confidence") or metadata.get("confidence")
        confidence_value: float | None = None
        if isinstance(confidence, (int, float)):
            confidence_value = float(confidence)

        updated_at = MemoryService._normalize_datetime(
            item.get("updated_at") or item.get("created_at") or metadata.get("updated_at") or metadata.get("created_at")
        )

        return {
            "id": str(fact_id),
            "fact_type": str(fact_type).strip() or "general",
            "fact_key": str(fact_key).strip(),
            "fact_value": fact_value,
            "confidence": confidence_value,
            "updated_at": updated_at,
        }

    async def list_facts(self, user_id: str, query: str | None = None, top_k: int = 50) -> list[dict[str, Any]]:
        if not user_id:
            return []

        scoped_user_id = self._memory_user_scope(str(user_id))
        if not scoped_user_id:
            return []

        try:
            raw_facts = await self.integration.list_facts(user_id=scoped_user_id, query=query, top_k=top_k)
            if not raw_facts:
                # Backward-compatibility with previously stored raw user_id memories.
                raw_facts = await self.integration.list_facts(user_id=str(user_id), query=query, top_k=top_k)

            normalized: list[dict[str, Any]] = []
            seen_ids: set[str] = set()
            for idx, item in enumerate(raw_facts):
                if not isinstance(item, dict):
                    continue
                fact = self._normalize_fact_item(item, idx)
                if fact is None:
                    continue
                if fact["id"] in seen_ids:
                    continue
                seen_ids.add(fact["id"])
                normalized.append(fact)

            return normalized
        except Exception:
            logger.debug("Facts listing failed", exc_info=True)
            return []

    async def add_fact(self, user_id: str, fact_type: str, fact_key: str, fact_value: str) -> dict[str, Any]:
        if not user_id:
            return {}

        scoped_user_id = self._memory_user_scope(str(user_id))
        if not scoped_user_id:
            return {}

        safe_type = (fact_type or "general").strip() or "general"
        safe_key = (fact_key or "").strip()
        safe_value = (fact_value or "").strip()
        if not safe_key or not safe_value:
            return {}

        try:
            created = await self.integration.add_fact(
                user_id=scoped_user_id,
                fact_type=safe_type,
                fact_key=safe_key,
                fact_value=safe_value,
            )
            normalized = self._normalize_fact_item(created if isinstance(created, dict) else {}, 0)
            if normalized:
                return normalized
            return {
                "id": "fact-created",
                "fact_type": safe_type,
                "fact_key": safe_key,
                "fact_value": safe_value,
                "confidence": None,
                "updated_at": None,
            }
        except Exception:
            logger.debug("Fact add failed", exc_info=True)
            return {}

    async def delete_fact(self, user_id: str, fact_id: str) -> bool:
        if not user_id or not fact_id:
            return False

        scoped_user_id = self._memory_user_scope(str(user_id))
        if not scoped_user_id:
            return False

        try:
            deleted = await self.integration.delete_fact(user_id=scoped_user_id, fact_id=fact_id)
            if deleted:
                return True
            # Backward-compatibility with previously stored raw user_id memories.
            return await self.integration.delete_fact(user_id=str(user_id), fact_id=fact_id)
        except Exception:
            logger.debug("Fact delete failed", exc_info=True)
            return False
