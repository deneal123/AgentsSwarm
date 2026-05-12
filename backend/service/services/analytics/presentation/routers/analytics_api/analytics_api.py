from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends

from service.composition.state import get_analytics_service
from service.services.analytics.presentation.routers.analytics_api.schemas import (
    IngestAcceptedResponse,
    VitalsBatchIn,
    VitalsSummaryResponse,
)
from service.services.analytics.application.analytics_service import AnalyticsService


analytics_router = APIRouter(prefix="/api/analytics")


@analytics_router.post("/vitals", response_model=IngestAcceptedResponse)
async def ingest_vitals(
    payload: Annotated[VitalsBatchIn, Body()],
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> IngestAcceptedResponse:
    enqueued = await service.ingest_vitals(payload.model_dump(mode="json"))
    return IngestAcceptedResponse(accepted=True, enqueued=enqueued)


@analytics_router.get("/vitals/summary", response_model=VitalsSummaryResponse)
async def vitals_summary(
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> VitalsSummaryResponse:
    result = await service.fetch_summary()
    return VitalsSummaryResponse.model_validate(result)
