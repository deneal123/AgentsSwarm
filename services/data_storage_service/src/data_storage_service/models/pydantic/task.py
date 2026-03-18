"""
Pydantic models for Celery tasks (Pushi)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from service.models.enums import TaskStatus, TaskType


class TaskResponse(BaseModel):
    """Task execution response"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    communication_task_id: UUID | None = None
    task_type: TaskType
    status: TaskStatus
    celery_task_id: str | None = None
    payload: dict = Field(default_factory=dict)
    result: dict | None = None
    error_message: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    priority: int = 0
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class UserTaskResponse(TaskResponse):
    """Compact task data returned for user task listings."""


class TaskCreate(BaseModel):
    """Create new task"""

    communication_task_id: UUID | None = None
    task_type: TaskType
    payload: dict = Field(default_factory=dict)
    scheduled_at: datetime | None = None
    priority: int = Field(default=0)


class TaskUpdate(BaseModel):
    """Update existing task"""

    status: TaskStatus | None = None
    result: dict | None = None
    error_message: str | None = None
    retry_count: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
