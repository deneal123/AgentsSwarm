"""
Health endpoints:
  GET /health  — liveness probe (всегда 200 если процесс жив)
  GET /ready   — readiness probe (200 если Redis и RabbitMQ доступны)
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse

from gateway_service.config import get_settings

router = APIRouter()
settings = get_settings()

# Время старта сервиса
_START_TIME = time.time()


@router.get("/health", include_in_schema=False)
async def health() -> ORJSONResponse:
    """Liveness probe — сервис жив."""
    return ORJSONResponse({
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "uptime_seconds": round(time.time() - _START_TIME, 1),
    })


@router.get("/ready", include_in_schema=False)
async def ready(request: Request) -> ORJSONResponse:
    """
    Readiness probe — все зависимости доступны.
    Проверяет: Redis PING, RabbitMQ connection state.
    """
    checks: dict[str, str] = {}
    all_ok = True

    # Redis
    redis = getattr(request.app.state, "redis", None)
    if redis:
        redis_ok = await redis.ping()
        checks["redis"] = "ok" if redis_ok else "unavailable"
        if not redis_ok:
            all_ok = False
    else:
        checks["redis"] = "not_initialized"
        all_ok = False

    # RabbitMQ
    rabbitmq = getattr(request.app.state, "rabbitmq", None)
    if rabbitmq:
        rmq_ok = await rabbitmq.is_healthy()
        checks["rabbitmq"] = "ok" if rmq_ok else "unavailable"
        if not rmq_ok:
            all_ok = False
    else:
        checks["rabbitmq"] = "not_initialized"
        all_ok = False

    status_code = 200 if all_ok else 503
    return ORJSONResponse(
        {
            "status": "ready" if all_ok else "not_ready",
            "checks": checks,
        },
        status_code=status_code,
    )
