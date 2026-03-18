"""Lightweight service layer for task-related operations.

This class sits between the FastAPI routers and the lower-level
``TaskRepository``/``TaskOrchestratorService``.  It provides simple
CRUD-style helpers used by the HTTP/WebSocket endpoints and keeps the
controllers free of repository details.

Most of the heavy lifting (dispatching Celery jobs, managing concurrency,
revoking tasks, etc.) is performed by ``TaskOrchestratorService``; the service
here delegates to it where appropriate but also exposes a minimal
repository-focused API for operations that simply read or write task records.

Methods return Pydantic models from ``service.models.pydantic.task`` so that
calling code can pass them straight through to FastAPI responses without
additional conversion.
"""

from __future__ import annotations

import logging
from typing import Any, List
from uuid import UUID

# Avoid importing `service.container` at module import time to prevent
# circular imports (container imports services module). The container
# will be imported lazily inside methods when needed.
from service.models.enums import TaskStatus, TaskType
from service.models.pydantic.task import (
    TaskCreate,
    TaskResponse,
    UserTaskResponse,
)
from service.repositories.task_repository import TaskRepository
from service.services.base_service import BaseService
from service.utils.logging_decorators import log_operation
from service.settings import TaskConfig

logger = logging.getLogger(__name__)


class TaskService(BaseService[TaskRepository]):
    """Service encapsulating basic task operations exposed to the API layer."""

    def __init__(self, config: TaskConfig, repository: TaskRepository) -> None:
        super().__init__(repository)
        self.config = config

    # ------------------------------------------------------------------
    # public convenience helpers used by routers
    # ------------------------------------------------------------------

    @log_operation(log_args=True, log_result=True)
    async def create_task(self, task_data: TaskCreate) -> TaskResponse:
        """Create a new task record and return its representation."""
        task = await self.repository.create_task(
            task_type=task_data.task_type,
            payload=task_data.payload,
            scheduled_at=task_data.scheduled_at,
            priority=task_data.priority,
            communication_task_id=task_data.communication_task_id,
            status=TaskStatus.NEW,
        )
        return TaskResponse.model_validate(task)

    @log_operation(log_args=True)
    async def get_user_tasks(
        self,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
        task_type: TaskType | None = None,
        status: TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[UserTaskResponse]:
        """Retrieve tasks for a user/guest with optional filtering."""
        tasks = await self.repository.get_tasks_by_user(
            user_id=user_id,
            guest_session_id=guest_session_id,
            task_type=task_type,
            status=status,
            limit=limit,
            offset=offset,
        )
        return [UserTaskResponse.model_validate(t) for t in tasks]

    @log_operation(log_args=True)
    async def get_task_status(self, task_id: UUID) -> TaskResponse | None:
        """Return the current state of a single task."""
        task = await self.repository.get_task_by_id(task_id)
        return TaskResponse.model_validate(task) if task else None

    @log_operation(log_args=True)
    async def cancel_task(self, task_id: UUID) -> TaskResponse | None:
        """Cancel a task using the orchestrator and return its new state.

        If the task cannot be found or cancelled, ``None`` is returned.  The
        orchestrator is responsible for revoking Celery jobs and releasing
        resources; we simply rely on its result and then read back the record
        so that callers can inform clients of the updated status.
        """
        # Import container lazily to avoid circular import during module load.
        from service.container import get, TaskOrchestratorServiceName

        orchestrator = get(TaskOrchestratorServiceName)
        cancelled = await orchestrator.cancel_task(task_id)
        if not cancelled:
            return None
        task = await orchestrator.get_task(task_id)
        return TaskResponse.model_validate(task) if task else None
