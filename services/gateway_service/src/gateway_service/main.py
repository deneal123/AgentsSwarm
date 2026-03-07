"""
Точка входа Gateway Service.

Жизненный цикл (lifespan):
  startup  → инициализация пулов Redis, RabbitMQ, gRPC-канала
  shutdown → graceful close всех соединений

Структура приложения:
  /health, /ready           — liveness / readiness probes
  /api/v1/...               — REST API
  /ws/chat, /ws/telemetry   — WebSocket
  /metrics                  — Prometheus (если включено)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import ORJSONResponse

from gateway_service.auth.exceptions import (
    AuthError,
    PermissionDeniedError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from gateway_service.config import get_settings
from gateway_service.middleware.logging import RequestLoggingMiddleware
from gateway_service.monitoring.logging import configure_logging
from gateway_service.monitoring.metrics import setup_metrics
from gateway_service.monitoring.tracing import setup_tracing
from gateway_service.services.grpc_client import get_grpc_client
from gateway_service.services.rabbitmq import RabbitMQPublisher
from gateway_service.services.redis_client import RedisClient
from gateway_service.ws.manager import get_connection_manager

logger = structlog.get_logger(__name__)
settings = get_settings()


# ─── Lifespan ─────────────────────────────────────────────────────────────────

async def _heartbeat_background(heartbeat_sec: int, timeout_sec: int) -> None:
    """Фоновая задача: пингует все WS-соединения и выгоняет зависшие."""
    import asyncio
    manager = get_connection_manager()
    while True:
        await asyncio.sleep(heartbeat_sec)
        try:
            await manager.ping_all()
            evicted = await manager.evict_stale(timeout_sec)
            if evicted:
                logger.info("ws.heartbeat.evicted", count=evicted)
        except Exception as exc:
            logger.warning("ws.heartbeat.error", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Инициализация и завершение всех подключений."""
    import asyncio
    log = structlog.get_logger("gateway.lifespan")

    # ── Startup ──────────────────────────────────────────────────────────────
    log.info("gateway.startup", environment=settings.environment)

    # Redis
    redis_client = RedisClient(url=settings.redis_url)
    await redis_client.connect()
    app.state.redis = redis_client
    log.info("redis.connected", url=settings.redis_url)

    # RabbitMQ
    rabbitmq = RabbitMQPublisher(url=settings.rabbitmq_url)
    await rabbitmq.connect()
    app.state.rabbitmq = rabbitmq
    log.info("rabbitmq.connected", url=settings.rabbitmq_url)

    # gRPC (Orchestrator)
    grpc_client = get_grpc_client()
    await grpc_client.connect()
    app.state.grpc_client = grpc_client
    log.info("grpc.connected", target=settings.grpc_target)

    # WebSocket heartbeat (фоновая задача)
    heartbeat_task = asyncio.create_task(
        _heartbeat_background(
            heartbeat_sec=settings.ws_heartbeat_seconds,
            timeout_sec=settings.ws_disconnect_timeout_seconds,
        )
    )
    log.info("ws.heartbeat_started", interval_sec=settings.ws_heartbeat_seconds)

    log.info("gateway.ready", port=settings.port)

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    log.info("gateway.shutdown")
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass
    await grpc_client.close()
    await rabbitmq.close()
    await redis_client.close()
    log.info("gateway.stopped")


# ─── Фабрика приложения ───────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Создать и настроить FastAPI приложение."""
    configure_logging(level=settings.log_level, environment=settings.environment)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API Gateway для платформы AgentsSwarm",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # ── Middleware (порядок важен: последний добавленный = первый в цепочке) ──

    # Доверенные хосты (защита от Host header injection)
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.trusted_hosts,
        )

    # CORS
    # В dev-режиме разрешаем все origins (credentials=False — ограничение браузера).
    # В prod — только явно заданные origins из конфига (settings.cors_origins).
    if settings.is_development:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,   # wildcard + credentials запрещены браузером
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=settings.cors_allow_methods,
            allow_headers=settings.cors_allow_headers,
        )

    # Структурированное логирование запросов + X-Request-ID / X-Trace-ID headers
    app.add_middleware(RequestLoggingMiddleware)

    # ── Глобальные обработчики исключений ────────────────────────────────────
    _register_exception_handlers(app)

    # ── Роутеры ───────────────────────────────────────────────────────────────
    from gateway_service.api.v1.router import api_v1_router
    from gateway_service.api.v1.health import router as health_router
    from gateway_service.ws.router import ws_router

    app.include_router(health_router, tags=["health"])
    app.include_router(api_v1_router, prefix="/api/v1")
    app.include_router(ws_router, prefix="/ws")

    # ── Observability ─────────────────────────────────────────────────────────
    if settings.metrics_enabled:
        setup_metrics(app)

    if settings.tracing_enabled and settings.otlp_endpoint:
        setup_tracing(
            app,
            endpoint=settings.otlp_endpoint,
            sample_rate=settings.tracing_sample_rate,
            service_name="gateway-service",
            service_version=settings.app_version,
        )

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """Глобальные обработчики исключений → унифицированный JSON-формат."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> ORJSONResponse:
        # Пробрасываем уже сформированные detail-объекты без изменений
        if isinstance(exc.detail, dict):
            content = exc.detail
        else:
            content = {"error_code": f"HTTP_{exc.status_code}", "message": str(exc.detail)}
        headers = dict(exc.headers) if exc.headers else {}
        return ORJSONResponse(status_code=exc.status_code, content=content, headers=headers)

    @app.exception_handler(AuthError)
    async def auth_error_handler(request: Request, exc: AuthError) -> ORJSONResponse:
        error_code = type(exc).__name__.upper().replace("ERROR", "_ERROR")
        logger.warning("auth.error", error=str(exc), path=request.url.path)
        return ORJSONResponse(
            status_code=401,
            content={"error_code": error_code, "message": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(PermissionDeniedError)
    async def permission_error_handler(request: Request, exc: PermissionDeniedError) -> ORJSONResponse:
        logger.warning("auth.permission_denied", error=str(exc), path=request.url.path)
        return ORJSONResponse(
            status_code=403,
            content={"error_code": "PERMISSION_DENIED", "message": str(exc)},
        )

    @app.exception_handler(UserNotFoundError)
    async def user_not_found_handler(request: Request, exc: UserNotFoundError) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=404,
            content={"error_code": "USER_NOT_FOUND", "message": str(exc)},
        )

    @app.exception_handler(UserAlreadyExistsError)
    async def user_conflict_handler(request: Request, exc: UserAlreadyExistsError) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=409,
            content={"error_code": "USER_ALREADY_EXISTS", "message": str(exc)},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> ORJSONResponse:
        # pydantic v2 может включать в ctx не-сериализуемые объекты (напр., ValueError)
        # Конвертируем их в строки для безопасной сериализации через orjson
        def _sanitize_error(err: dict) -> dict:
            sanitized = {k: v for k, v in err.items() if k != "ctx"}
            if "ctx" in err:
                sanitized["ctx"] = {
                    k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
                    for k, v in err["ctx"].items()
                }
            return sanitized

        sanitized_errors = [_sanitize_error(e) for e in exc.errors()]
        logger.debug("validation.error", errors=sanitized_errors, path=request.url.path)
        return ORJSONResponse(
            status_code=422,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": sanitized_errors,
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> ORJSONResponse:
        from gateway_service.monitoring.tracing import get_trace_id  # noqa: PLC0415
        trace_id = get_trace_id()
        logger.exception(
            "unhandled.error",
            error=str(exc),
            path=request.url.path,
            trace_id=trace_id,
        )
        return ORJSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                **({"trace_id": trace_id} if trace_id else {}),
            },
        )



# ─── Singleton app ───────────────────────────────────────────────────────────
app = create_app()


# ─── Dev entrypoint ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "gateway_service.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_config=None,  # structlog управляет логированием
    )
