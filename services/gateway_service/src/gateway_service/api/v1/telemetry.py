"""
Роутер телеметрии — исторические временны́е ряды из InfluxDB.

Эндпоинты:
  GET /telemetry/{robot_id} — исторические данные телеметрии

Данные запрашиваются напрямую из InfluxDB или через Orchestrator gRPC.
До реализации (Этап 6) возвращаются mock-данные / заглушка.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

from gateway_service.auth.permissions import require_authenticated
from gateway_service.auth.schemas import UserContext
from gateway_service.schemas.telemetry import TelemetryHistory, TelemetryResolution

logger = structlog.get_logger(__name__)

router = APIRouter()

_DEFAULT_RANGE_HOURS = 1
_MAX_RANGE_DAYS = 30


@router.get(
    "/{robot_id}",
    response_model=TelemetryHistory,
    summary="Историческая телеметрия робота",
    description=(
        "Возвращает временны́е ряды телеметрии за указанный период. "
        "Поддерживает агрегацию: raw, 10s, 1m, 5m, 15m, 1h, 6h, 1d."
    ),
    responses={
        200: {"description": "Данные телеметрии"},
        400: {"description": "Некорректный временной диапазон"},
        404: {"description": "Данных для указанного робота нет"},
    },
)
async def get_telemetry(
    robot_id: str,
    from_ts: datetime | None = Query(
        default=None,
        alias="from",
        description="Начало диапазона (ISO 8601). По умолчанию: 1 час назад.",
    ),
    to_ts: datetime | None = Query(
        default=None,
        alias="to",
        description="Конец диапазона (ISO 8601). По умолчанию: сейчас.",
    ),
    resolution: TelemetryResolution = Query(
        default=TelemetryResolution.MIN1,
        description="Гранулярность агрегации",
    ),
    current_user: UserContext = Depends(require_authenticated),
) -> TelemetryHistory:
    now = datetime.now(tz=timezone.utc)

    # Defaults
    if to_ts is None:
        to_ts = now
    if from_ts is None:
        from_ts = to_ts - timedelta(hours=_DEFAULT_RANGE_HOURS)

    # Убираем tzinfo для унификации (InfluxDB работает с UTC naive)
    if from_ts.tzinfo is not None:
        from_ts = from_ts.replace(tzinfo=None)
    if to_ts.tzinfo is not None:
        to_ts = to_ts.replace(tzinfo=None)

    # Валидация диапазона
    if from_ts >= to_ts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_TIME_RANGE", "message": "'from' must be before 'to'"},
        )
    max_range = timedelta(days=_MAX_RANGE_DAYS)
    if (to_ts - from_ts) > max_range:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "RANGE_TOO_LARGE",
                "message": f"Maximum time range is {_MAX_RANGE_DAYS} days",
            },
        )

    logger.info(
        "telemetry.query",
        user_id=current_user.user_id,
        robot_id=robot_id,
        from_ts=from_ts.isoformat(),
        to_ts=to_ts.isoformat(),
        resolution=resolution.value,
    )

    # TODO (Этап 6): запрос к InfluxDB через influxdb-client-python
    #   query = f'''
    #     from(bucket: "telemetry")
    #       |> range(start: {from_ts.isoformat()}Z, stop: {to_ts.isoformat()}Z)
    #       |> filter(fn: (r) => r.robot_id == "{robot_id}")
    #       |> aggregateWindow(every: {resolution.value}, fn: mean)
    #   '''
    # Пока возвращаем пустой ответ (не 404, т.к. робот может быть новым)
    return TelemetryHistory(
        robot_id=robot_id,
        from_ts=from_ts,
        to_ts=to_ts,
        resolution=resolution,
        points=[],
        total_points=0,
    )
