"""Схемы для эндпоинтов Playground (анализ коммуникаций в интерактивном режиме)."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Re-export task response
from service.models.pydantic.task import TaskResponse as TaskResponse  # noqa: F401


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class AnalyzeCommunicationRequest(BaseModel):
    """Запрос на анализ одной или нескольких коммуникаций."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "communications": [
                    {
                        "text": "Получите кредит под 0% без переплат!",
                        "type": "push",
                        "product_type": "кредит",
                        "ai": 0,
                    }
                ]
            }
        }
    )

    communications: list[dict[str, Any]] | dict[str, Any] = Field(
        ...,
        description="Одна коммуникация (dict) или список коммуникаций (list[dict])",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class PlaygroundTaskCancelResponse(BaseModel):
    """Ответ на отмену задачи playground."""

    message: str
    task_id: UUID
    cancelled: bool


class PlaygroundResultsResponse(BaseModel):
    """Результаты анализа playground-задачи (свободная структура, зависит от задачи)."""

    task_id: UUID
    results: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
