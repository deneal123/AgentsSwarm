from __future__ import annotations

import asyncio

from service.services.analytics.persistence.analytics_repository import AnalyticsVitalsRepository


class AnalyticsService:
    def __init__(self, repository: AnalyticsVitalsRepository) -> None:
        self._repository = repository

    async def ingest_vitals(self, payload: dict) -> int:
        asyncio.create_task(self._repository.persist_batch(payload))
        events = payload.get("events")
        return len(events) if isinstance(events, list) else 0

    async def fetch_summary(self) -> dict:
        return await self._repository.fetch_summary()
