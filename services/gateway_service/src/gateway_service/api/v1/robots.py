"""
Роутер для роботов.

Эндпоинты:
  GET  /robots                              — список роботов (пагинация, фильтрация)
  GET  /robots/{robot_id}                   — состояние конкретного робота
  GET  /robots/{robot_id}/telemetry         — текущая телеметрия робота
  POST /robots/{robot_id}/emergency_stop    — аварийная остановка робота

Данные запрашиваются через gRPC-клиент к Orchestrator.
До реализации gRPC-клиента (Этап 6) используется заглушка.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from gateway_service.auth.middleware import get_current_user
from gateway_service.auth.permissions import require_authenticated, require_operator
from gateway_service.auth.schemas import UserContext
from gateway_service.schemas.common import MessageResponse, PaginatedResponse, PaginationParams, pagination_params
from gateway_service.schemas.robot import (
    RobotDetail,
    RobotListFilters,
    RobotStatus,
    RobotSummary,
    RobotTelemetry,
)

logger = structlog.get_logger(__name__)

router = APIRouter()


# ─── Stub helpers ─────────────────────────────────────────────────────────────


def _get_grpc_client(request_obj: object = None) -> object:  # type: ignore[return]
    """
    Заглушка: в Этапе 6 будет заменена на gRPC-клиент.
    Возвращает None — роутеры обрабатывают этот случай.
    """
    return None


# ─── GET /robots ──────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=PaginatedResponse[RobotSummary],
    summary="Список роботов",
    description="Возвращает постраничный список роботов с опциональной фильтрацией.",
)
async def list_robots(
    status: RobotStatus | None = Query(default=None, description="Фильтр по статусу"),
    zone_id: str | None = Query(default=None, description="Фильтр по зоне"),
    has_task: bool | None = Query(default=None, description="Только с активной задачей"),
    pagination: PaginationParams = Depends(pagination_params),
    current_user: UserContext = Depends(require_authenticated),
) -> PaginatedResponse[RobotSummary]:
    logger.info(
        "robots.list",
        user_id=current_user.user_id,
        filters={"status": status, "zone_id": zone_id, "has_task": has_task},
        page=pagination.page,
    )

    # TODO (Этап 6): запрос к Orchestrator gRPC
    # grpc_client = request.app.state.grpc_client
    # response = await grpc_client.list_robots(status=status, zone_id=zone_id, ...)
    # Пока возвращаем пустой список
    return PaginatedResponse.create(
        items=[],
        total=0,
        page=pagination.page,
        page_size=pagination.page_size,
    )


# ─── GET /robots/{robot_id} ───────────────────────────────────────────────────


@router.get(
    "/{robot_id}",
    response_model=RobotDetail,
    summary="Состояние робота",
    responses={
        404: {"description": "Робот не найден"},
    },
)
async def get_robot(
    robot_id: str,
    current_user: UserContext = Depends(require_authenticated),
) -> RobotDetail:
    logger.info("robots.get", user_id=current_user.user_id, robot_id=robot_id)

    # TODO (Этап 6): grpc_client.get_robot_state(robot_id)
    # Временная заглушка — возвращаем 404 для несуществующих роботов
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error_code": "ROBOT_NOT_FOUND", "message": f"Robot '{robot_id}' not found"},
    )


# ─── GET /robots/{robot_id}/telemetry ────────────────────────────────────────


@router.get(
    "/{robot_id}/telemetry",
    response_model=RobotTelemetry,
    summary="Текущая телеметрия робота",
    description="Возвращает последний снимок телеметрии: позицию, батарею, сенсоры, события.",
    responses={
        404: {"description": "Робот не найден или нет данных телеметрии"},
    },
)
async def get_robot_telemetry(
    robot_id: str,
    current_user: UserContext = Depends(require_authenticated),
) -> RobotTelemetry:
    logger.info("robots.telemetry", user_id=current_user.user_id, robot_id=robot_id)

    # TODO (Этап 6): grpc_client.get_robot_state(robot_id) → маппинг в RobotTelemetry
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error_code": "ROBOT_NOT_FOUND", "message": f"Robot '{robot_id}' not found"},
    )


# ─── POST /robots/{robot_id}/emergency_stop ───────────────────────────────────


@router.post(
    "/{robot_id}/emergency_stop",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Аварийная остановка робота",
    description=(
        "Немедленно останавливает выполнение всех задач робота. "
        "Требует роль OPERATOR или выше. "
        "Команда публикуется в RabbitMQ с максимальным приоритетом."
    ),
    responses={
        200: {"description": "Команда остановки отправлена"},
        404: {"description": "Робот не найден"},
        503: {"description": "RabbitMQ недоступен"},
    },
)
async def emergency_stop(
    robot_id: str,
    request: Request,
    current_user: UserContext = Depends(require_operator),
) -> MessageResponse:
    logger.warning(
        "robots.emergency_stop",
        robot_id=robot_id,
        user_id=current_user.user_id,
    )

    # Публикуем команду в RabbitMQ
    rabbitmq = getattr(request.app.state, "rabbitmq", None)
    if rabbitmq is not None:
        try:
            await rabbitmq.publish(
                routing_key="robots.commands",
                message={
                    "type": "emergency_stop",
                    "robot_id": robot_id,
                    "user_id": current_user.user_id,
                    "priority": 100,
                },
                priority=10,
            )
        except Exception as exc:
            logger.error("robots.emergency_stop.rabbitmq_failed", robot_id=robot_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error_code": "MESSAGING_UNAVAILABLE",
                    "message": "Failed to publish emergency stop command",
                },
            )

    return MessageResponse(message=f"Emergency stop command sent for robot '{robot_id}'")
