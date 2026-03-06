"""
Pydantic-схемы для рабочих зон (zones).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ─── Bounding Box ────────────────────────────────────────────────────────────


class ZoneBounds(BaseModel):
    """Прямоугольная граница зоны в системе координат карты."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def area(self) -> float:
        return max(0.0, (self.x_max - self.x_min) * (self.y_max - self.y_min))


# ─── Zone CRUD ───────────────────────────────────────────────────────────────


class ZoneCreate(BaseModel):
    """Тело запроса POST /zones."""

    name: str = Field(min_length=1, max_length=128, description="Название зоны")
    description: str = Field(default="", max_length=1000)
    bounds: ZoneBounds
    map_id: str = Field(default="default", description="Идентификатор карты")
    max_robots: int = Field(default=10, ge=1, le=100, description="Максимум роботов одновременно")
    is_restricted: bool = Field(default=False, description="Ограниченный доступ")
    metadata: dict[str, str] = Field(default_factory=dict)


class ZoneUpdate(BaseModel):
    """Тело запроса PUT /zones/{id}."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=1000)
    bounds: ZoneBounds | None = None
    max_robots: int | None = Field(default=None, ge=1, le=100)
    is_restricted: bool | None = None
    is_active: bool | None = None
    metadata: dict[str, str] | None = None


class ZoneDetail(BaseModel):
    """Полная информация о зоне."""

    zone_id: str
    name: str
    description: str = ""
    bounds: ZoneBounds
    map_id: str = "default"
    max_robots: int = 10
    is_restricted: bool = False
    is_active: bool = True
    robot_count: int = Field(default=0, description="Роботов в зоне сейчас")
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ZoneSummary(BaseModel):
    """Краткое представление зоны для списков."""

    zone_id: str
    name: str
    is_active: bool = True
    is_restricted: bool = False
    robot_count: int = 0
    max_robots: int = 10
