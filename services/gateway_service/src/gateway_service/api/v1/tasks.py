"""
Роутер для задач.

Эндпоинты:
  GET  /tasks                 — список задач (пагинация, фильтрация)
  GET  /tasks/{task_id}       — детали задачи
  POST /tasks                 — создать задачу (publish → RabbitMQ → Orchestrator)
  PUT  /tasks/{task_id}/cancel — отменить задачу

Создание задачи использует RabbitMQ (Этап 6).
Чтение статуса — gRPC к Orchestrator (Этап 6).
"""

from __future__ import annotations

import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from gateway_service.auth.permissions import require_authenticated, require_operator
from gateway_service.auth.schemas import UserContext
from gateway_service.schemas.common import PaginatedResponse, PaginationParams, pagination_params
from gateway_service.schemas.task import (
    TaskCancel,
    TaskCreate,
    TaskDetail,
    TaskStatus,
    TaskSummary,
)

logger = structlog.get_logger(__name__)

router = APIRouter()


# ─── GET /tasks ───────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=PaginatedResponse[TaskSummary],
    summary="Список задач",
)
async def list_tasks(
    task_status: TaskStatus | None = Query(default=None, alias="status"),
    robot_id: str | None = Query(default=None),
    zone_id: str | None = Query(default=None),
    pagination: PaginationParams = Depends(pagination_params),
    current_user: UserContext = Depends(require_authenticated),
) -> PaginatedResponse[TaskSummary]:
    logger.info(
        "tasks.list",
        user_id=current_user.user_id,
        filters={"status": task_status, "robot_id": robot_id, "zone_id": zone_id},
    )

    # TODO (Этап 6): grpc_client.list_tasks(filters, pagination)
    return PaginatedResponse.create(items=[], total=0, page=pagination.page, page_size=pagination.page_size)


# ─── GET /tasks/{task_id} ─────────────────────────────────────────────────────


@router.get(
    "/{task_id}",
    response_model=TaskDetail,
    summary="Детали задачи",
    responses={404: {"description": "Задача не найдена"}},
)
async def get_task(
    task_id: str,
    current_user: UserContext = Depends(require_authenticated),
) -> TaskDetail:
    logger.info("tasks.get", user_id=current_user.user_id, task_id=task_id)

    # TODO (Этап 6): grpc_client.get_task_status(task_id)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error_code": "TASK_NOT_FOUND", "message": f"Task '{task_id}' not found"},
    )


# ─── POST /tasks ──────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=TaskDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Создать задачу",
    description="Публикует команду в RabbitMQ. Orchestrator подхватит и вернёт task_id.",
    responses={
        201: {"description": "Задача принята в обработку"},
        503: {"description": "RabbitMQ недоступен"},
    },
)
async def create_task(
    body: TaskCreate,
    request: Request,
    current_user: UserContext = Depends(require_operator),
) -> TaskDetail:
    task_id = str(uuid.uuid4())
    logger.info(
        "tasks.create",
        user_id=current_user.user_id,
        task_id=task_id,
        priority=body.priority,
    )

    # Публикуем команду в RabbitMQ
    rabbitmq = getattr(request.app.state, "rabbitmq", None)
    if rabbitmq:
        try:
            await rabbitmq.publish_command(
                routing_key="task.create",
                payload={
                    "task_id": task_id,
                    "user_id": current_user.user_id,
                    "text": body.text,
                    "priority": body.priority,
                    "robot_id": body.robot_id,
                    "zone_id": body.zone_id,
                },
                message_id=task_id,
            )
        except Exception as exc:
            logger.error("tasks.rabbitmq_publish_failed", task_id=task_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error_code": "QUEUE_UNAVAILABLE", "message": "Failed to submit task"},
            ) from exc
    else:
        logger.warning("tasks.rabbitmq_not_available", task_id=task_id)

    return TaskDetail(
        task_id=task_id,
        status=TaskStatus.PENDING,
        text=body.text,
        priority=body.priority,
        assigned_robot_id=body.robot_id,
        zone_id=body.zone_id,
        created_at=datetime.utcnow(),
    )


# ─── PUT /tasks/{task_id}/cancel ──────────────────────────────────────────────


@router.put(
    "/{task_id}/cancel",
    response_model=TaskDetail,
    summary="Отменить задачу",
    responses={
        404: {"description": "Задача не найдена"},
        409: {"description": "Задача уже завершена или отменена"},
    },
)
async def cancel_task(
    task_id: str,
    body: TaskCancel,
    request: Request,
    current_user: UserContext = Depends(require_operator),
) -> TaskDetail:
    logger.info(
        "tasks.cancel",
        user_id=current_user.user_id,
        task_id=task_id,
        reason=body.reason,
    )

    # Публикуем событие отмены в RabbitMQ
    rabbitmq = getattr(request.app.state, "rabbitmq", None)
    if rabbitmq:
        try:
            await rabbitmq.publish_command(
                routing_key="task.cancel",
                payload={"task_id": task_id, "user_id": current_user.user_id, "reason": body.reason},
                message_id=f"cancel-{task_id}",
            )
        except Exception as exc:
            logger.error("tasks.cancel_publish_failed", task_id=task_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error_code": "QUEUE_UNAVAILABLE", "message": "Failed to cancel task"},
            ) from exc

    # TODO (Этап 6): получить актуальный статус через grpc_client.get_task_status
    return TaskDetail(
        task_id=task_id,
        status=TaskStatus.CANCELLED,
        text="",
        priority=50,
    )
