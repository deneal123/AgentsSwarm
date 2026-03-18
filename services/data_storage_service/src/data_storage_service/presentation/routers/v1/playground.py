"""Playground endpoints for interactive risk analysis."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from service.models.enums import TaskStatus
from service.presentation.schemas.playground import (
    AnalyzeCommunicationRequest,
    PlaygroundTaskCancelResponse,
    TaskResponse,
)
from service.presentation.dependencies.auth import get_current_user_or_guest
from service.presentation.dependencies.services import get_playground_logic

logger = logging.getLogger(__name__)

playground_router = APIRouter(prefix="/api/v1/playground", tags=["Playground"])


@playground_router.post(
    "/analyze",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Запустить анализ коммуникаций",
    description="Передаёт одну или несколько коммуникаций на анализ в режиме playground. Возвращает задачу для отслеживания.",
)
async def analyze_communications(
    body: AnalyzeCommunicationRequest,
    max_parallel_batches: int = Query(
        3,
        description="Максимум параллельных батчей (1-10)",
        ge=1,
        le=10,
    ),
    batch_size: int = Query(
        10,
        description="Размер батча",
        ge=1,
        le=1000,
    ),
    config_file_id: UUID | None = Query(
        None,
        description="UUID загруженного конфиг-файла (опционально)",
    ),
    playground_logic=Depends(get_playground_logic),
    user_or_guest=Depends(get_current_user_or_guest),
):
    """Анализ коммуникаций в playground."""
    user_id = user_or_guest.get("user_id")
    guest_session_id = user_or_guest.get("guest_session_id")

    communications = body.communications
    # Normalize to list
    if isinstance(communications, dict):
        communications = [communications]

    # Build config
    config = {
        "max_parallel_batches": max_parallel_batches,
        "batch_size": batch_size,
    }

    task_info = await playground_logic.analyze_communications(
        communications=communications,
        config=config,
        config_file_id=config_file_id,
        user_id=user_id,
        guest_session_id=guest_session_id,
    )

    # Get full task info
    task_id = task_info["task_id"]
    task = await playground_logic.get_task_status(task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    return TaskResponse(
        id=task_id,
        task_type=task_info["task_type"],
        status=task["status"],
        created_at=task.get("created_at"),
        started_at=task.get("started_at"),
        completed_at=task.get("completed_at"),
        error_message=task.get("error_message"),
        payload={"communications": communications},
        result=None,
    )


@playground_router.get(
    "/results/{task_id}",
    summary="Результаты анализа",
    description="Возвращает результаты задачи анализа в playground.",
)
async def get_results(
    task_id: UUID,
    playground_logic=Depends(get_playground_logic),
    user_or_guest=Depends(get_current_user_or_guest),
):
    """Get analysis results for a task."""
    user_id = user_or_guest.get("user_id")
    guest_session_id = user_or_guest.get("guest_session_id")

    results = await playground_logic.get_results(
        task_id=task_id,
        user_id=user_id,
        guest_session_id=guest_session_id,
    )

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No results found for task {task_id}",
        )

    return results


@playground_router.get(
    "/tasks",
    response_model=list[TaskResponse],
    summary="Список задач пользователя",
    description="Возвращает задачи playground текущего пользователя или гостя.",
)
async def list_user_tasks(
    status: TaskStatus | None = Query(
        None,
        description="Filter by task status",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        0,
        ge=0,
    ),
    playground_logic=Depends(get_playground_logic),
    user_or_guest=Depends(get_current_user_or_guest),
):
    """List user's/guest's playground tasks."""
    user_id = user_or_guest.get("user_id")
    guest_session_id = user_or_guest.get("guest_session_id")

    tasks = await playground_logic.list_user_tasks(
        user_id=user_id,
        guest_session_id=guest_session_id,
        limit=limit,
        offset=offset,
    )

    return tasks


@playground_router.get(
    "/tasks/{task_id}",
    summary="Статус задачи playground",
    description=(
        "Возвращает текущий статус задачи playground и информацию о прогрессе — "
        "включая прогресс по батчам при обработке."
    ),
)
async def get_task_status(
    task_id: UUID,
    playground_logic=Depends(get_playground_logic),
    user_or_guest=Depends(get_current_user_or_guest),
):
    """Return current status and progress of a playground task."""
    task = await playground_logic.get_task_status(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    return task


@playground_router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_200_OK,
    response_model=PlaygroundTaskCancelResponse,
    summary="Отменить задачу playground",
    description="Отменяет задачу playground, если она находится в статусах NEW, PENDING или PROCESSING.",
)
async def cancel_task(
    task_id: UUID,
    playground_logic=Depends(get_playground_logic),
    user_or_guest=Depends(get_current_user_or_guest),
):
    """Cancel a playground task. Raises 403 if the task belongs to another user."""
    user_id = user_or_guest.get("user_id")
    guest_session_id = user_or_guest.get("guest_session_id")

    cancelled = await playground_logic.cancel_task(
        task_id=task_id,
        user_id=user_id,
        guest_session_id=guest_session_id,
    )

    return PlaygroundTaskCancelResponse(
        message="Задача успешно отменена",
        task_id=task_id,
        cancelled=cancelled,
    )