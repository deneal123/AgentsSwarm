from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Body, Depends

from service.presentation.dependencies import providers
from service.presentation.routers.analytics_api.schemas import (
    IngestAcceptedResponse,
    VitalsBatchIn,
    VitalsSummaryResponse,
)
from service.repositories.analytics_vitals_repository import AnalyticsVitalsRepository


analytics_router = APIRouter(prefix="/api/analytics")


def get_analytics_repository(
    redis_client=Depends(providers.get_optional_redis_client),
) -> AnalyticsVitalsRepository:
    return AnalyticsVitalsRepository(redis_client=redis_client)


@analytics_router.post("/vitals", response_model=IngestAcceptedResponse)
async def ingest_vitals(
    payload: Annotated[VitalsBatchIn, Body()],
    repository: Annotated[AnalyticsVitalsRepository, Depends(get_analytics_repository)],
) -> IngestAcceptedResponse:
    asyncio.create_task(repository.persist_batch(payload.model_dump(mode="json")))
    return IngestAcceptedResponse(accepted=True, enqueued=len(payload.events))


@analytics_router.get("/vitals/summary", response_model=VitalsSummaryResponse)
async def vitals_summary(
    repository: Annotated[AnalyticsVitalsRepository, Depends(get_analytics_repository)],
) -> VitalsSummaryResponse:
    result = await repository.fetch_summary()
    return VitalsSummaryResponse.model_validate(result)
