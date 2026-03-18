"""Схемы для эндпоинтов Pipeline (пакетный анализ датасетов)."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Re-export task response
from service.models.pydantic.task import TaskResponse as TaskResponse  # noqa: F401


class PipelineTaskCancelResponse(BaseModel):
    """Ответ на отмену задачи pipeline."""

    message: str
    task_id: UUID
    cancelled: bool


class PipelineReportSummary(BaseModel):
    """Краткая сводка отчёта pipeline (для списка отчётов)."""

    task_id: UUID
    status: str
    dataset_file_id: UUID | None = None
    created_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None


class PipelineReportDetail(BaseModel):
    """Полные данные отчёта по завершённой задаче pipeline."""

    task_id: UUID
    status: str
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    artifacts: list[str] = Field(
        default_factory=list,
        description="Список путей к артефактам (xlsx, pdf и т.д.) для скачивания",
    )
    error_message: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
