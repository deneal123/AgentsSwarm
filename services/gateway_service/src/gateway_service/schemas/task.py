"""
Pydantic-схемы для задач.
Соответствуют proto-контракту common/v1/types.proto + orchestrator/v1/orchestrator.proto.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ─── Enums ───────────────────────────────────────────────────────────────────


class TaskStatus(str, Enum):
    """Статус задачи (синхронизирован с proto TaskStatus)."""

    UNSPECIFIED = "unspecified"
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ─── Create / Cancel ──────────────────────────────────────────────────────────


class TaskCreate(BaseModel):
    """Тело запроса POST /tasks."""

    text: str = Field(
        min_length=1,
        max_length=1000,
        description="Описание задачи на естественном языке",
    )
    priority: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Приоритет задачи: 1 (низкий) … 100 (экстренный)",
    )
    robot_id: str | None = Field(
        default=None,
        description="Конкретный робот-исполнитель (None = авто-выбор оркестратора)",
    )
    zone_id: str | None = Field(
        default=None,
        description="Зона выполнения (ограничить выбор роботов)",
    )


class TaskCancel(BaseModel):
    """Тело запроса PUT /tasks/{id}/cancel."""

    reason: str = Field(default="User cancelled", max_length=500)


# ─── Detail ──────────────────────────────────────────────────────────────────


class TaskDetail(BaseModel):
    """Полная информация о задаче (ответ GET /tasks/{id})."""

    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    text: str
    priority: int = Field(ge=1, le=100)
    assigned_robot_id: str | None = None
    zone_id: str | None = None
    progress_message: str | None = None
    result: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class TaskSummary(BaseModel):
    """Краткое представление задачи для списков."""

    task_id: str
    status: TaskStatus
    priority: int
    assigned_robot_id: str | None = None
    progress_message: str | None = None
    created_at: datetime | None = None


# ─── Фильтры ─────────────────────────────────────────────────────────────────


class TaskListFilters(BaseModel):
    """Фильтры для GET /tasks."""

    status: TaskStatus | None = None
    robot_id: str | None = None
    zone_id: str | None = None
