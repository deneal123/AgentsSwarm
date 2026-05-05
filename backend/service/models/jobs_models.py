import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from service.models.key_value import ProcessingStatus, ServiceType


class JobLogic(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    type: ServiceType
    status: ProcessingStatus
    # Поля источников/результатов исключены до внедрения таблицы файлов/результатов
    created_at: datetime | None = None
    updated_at: datetime | None = None
    payload: dict[str, Any] | None = None

    # Celery task tracking
    celery_task_id: str | None = None  # Link to Celery task
    celery_status: str | None = None   # Celery task status

    model_config = ConfigDict(from_attributes=True)
