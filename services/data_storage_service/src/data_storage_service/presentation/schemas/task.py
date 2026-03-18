"""Схемы задач для API-слоя.

Для задач используется единая модель TaskResponse из domain-слоя.
Здесь определяются специфические запросы и вспомогательные ответы.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# Re-export domain response (источник правды)
from service.models.pydantic.task import TaskResponse as TaskResponse  # noqa: F401


class TaskCancelResponse(BaseModel):
    """Ответ на отмену задачи."""

    message: str
    task_id: UUID
    cancelled: bool


class TaskStatusShort(BaseModel):
    """Сокращённый статус задачи для polling."""

    id: UUID
    status: str
    error_message: str | None = None
    completed_at: datetime | None = None
