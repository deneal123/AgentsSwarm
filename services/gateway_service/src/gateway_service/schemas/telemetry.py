"""
Pydantic-схемы для временны́х рядов телеметрии (InfluxDB).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TelemetryResolution(str, Enum):
    """Гранулярность агрегации для исторических запросов."""

    RAW = "raw"        # без агрегации
    S10 = "10s"        # 10 секунд
    MIN1 = "1m"        # 1 минута
    MIN5 = "5m"        # 5 минут
    MIN15 = "15m"      # 15 минут
    HOUR1 = "1h"       # 1 час
    HOUR6 = "6h"       # 6 часов
    DAY1 = "1d"        # сутки


class TelemetryPoint(BaseModel):
    """Одна точка временного ряда."""

    timestamp: datetime
    battery_level: float | None = Field(default=None, ge=0.0, le=100.0)
    velocity: float | None = None
    position_x: float | None = None
    position_y: float | None = None
    status: str | None = None
    extra: dict[str, float] = Field(default_factory=dict, description="Дополнительные метрики сенсоров")


class TelemetryHistory(BaseModel):
    """Ответ GET /telemetry/{robot_id} — исторические данные."""

    robot_id: str
    from_ts: datetime
    to_ts: datetime
    resolution: TelemetryResolution = TelemetryResolution.MIN1
    points: list[TelemetryPoint] = Field(default_factory=list)
    total_points: int = 0
