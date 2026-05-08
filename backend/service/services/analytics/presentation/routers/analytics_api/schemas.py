from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator


class VitalMetricIn(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=32)]
    value: Annotated[float, Field(ge=0)]
    rating: Annotated[Literal["good", "needs-improvement", "poor", "unknown"], Field()]
    navigation_type: Annotated[str | None, Field(default=None, max_length=64)]
    metric_id: Annotated[str | None, Field(default=None, max_length=128)]
    delta: Annotated[float | None, Field(default=None)]
    recorded_at: Annotated[datetime | None, Field(default=None)]


class VitalsBatchIn(BaseModel):
    version: Annotated[str, Field(min_length=1, max_length=16)]
    sampled: bool = True
    session_id: Annotated[str | None, Field(default=None, max_length=128)]
    user_id_hash: Annotated[str | None, Field(default=None, max_length=128)]
    page: Annotated[str | None, Field(default=None, max_length=2048)]
    user_agent: Annotated[str | None, Field(default=None, max_length=1024)]
    events: Annotated[list[VitalMetricIn], Field(min_length=1, max_length=100)]

    @field_validator("version")
    @classmethod
    def normalize_version(cls, value: str) -> str:
        return value.strip()


class IngestAcceptedResponse(BaseModel):
    accepted: bool
    enqueued: int


class MetricAggregate(BaseModel):
    name: str
    count: int
    avg: float
    p95: float
    good_rate: float
    needs_improvement_rate: float
    poor_rate: float


class VitalsSummaryResponse(BaseModel):
    updated_at: datetime
    total_events: int
    metrics: list[MetricAggregate]
