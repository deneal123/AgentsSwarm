"""
Pydantic-схемы для роботов.
Соответствуют proto-контракту common/v1/types.proto + orchestrator/v1/orchestrator.proto.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ─── Enums ───────────────────────────────────────────────────────────────────


class RobotStatus(str, Enum):
    """Статус робота (синхронизирован с proto RobotStatus)."""

    UNSPECIFIED = "unspecified"
    IDLE = "idle"
    MOVING = "moving"
    EXECUTING = "executing"
    CHARGING = "charging"
    ERROR = "error"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


# ─── Позиция ─────────────────────────────────────────────────────────────────


class Position(BaseModel):
    """Пространственное положение робота."""

    x: float = Field(description="Координата X, метры")
    y: float = Field(description="Координата Y, метры")
    z: float = Field(default=0.0, description="Координата Z, метры")
    orientation_x: float = Field(default=0.0, description="Кватернион Qx")
    orientation_y: float = Field(default=0.0, description="Кватернион Qy")
    orientation_z: float = Field(default=0.0, description="Кватернион Qz")
    orientation_w: float = Field(default=1.0, description="Кватернион Qw")
    frame_id: str = Field(default="map", description="Система координат: map | odom | base_link")


# ─── Robot Detail ─────────────────────────────────────────────────────────────


class RobotDetail(BaseModel):
    """Полное состояние робота (ответ GET /robots/{id})."""

    robot_id: str
    status: RobotStatus = RobotStatus.UNSPECIFIED
    position: Position | None = None
    battery_level: float = Field(default=0.0, ge=0.0, le=100.0, description="Заряд батареи, %")
    zone_id: str | None = None
    current_task_id: str | None = None
    last_seen: datetime | None = None


class RobotSummary(BaseModel):
    """Краткое представление робота для списков."""

    robot_id: str
    status: RobotStatus = RobotStatus.UNSPECIFIED
    battery_level: float = Field(default=0.0, ge=0.0, le=100.0)
    zone_id: str | None = None
    current_task_id: str | None = None
    last_seen: datetime | None = None


# ─── Robot List ───────────────────────────────────────────────────────────────


class RobotListFilters(BaseModel):
    """Фильтры для GET /robots."""

    status: RobotStatus | None = None
    zone_id: str | None = None
    has_task: bool | None = None


# ─── Robot Telemetry ──────────────────────────────────────────────────────────


class SensorDataItem(BaseModel):
    """Показания одного сенсора."""

    sensor_type: str
    timestamp: datetime
    values: dict[str, float] = Field(default_factory=dict)


class RobotEventItem(BaseModel):
    """Событие робота."""

    event_type: str
    severity: str = "low"
    description: str
    metadata: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime


class RobotTelemetry(BaseModel):
    """Полная телеметрия робота (ответ GET /robots/{id}/telemetry)."""

    robot_id: str
    timestamp: datetime
    status: RobotStatus = RobotStatus.UNSPECIFIED
    position: Position | None = None
    battery_level: float = Field(ge=0.0, le=100.0)
    velocity: float = Field(default=0.0, description="Скорость, м/с")
    sensors: dict[str, SensorDataItem] = Field(default_factory=dict)
    events: list[RobotEventItem] = Field(default_factory=list)
    current_task_id: str | None = None
    zone_id: str | None = None
