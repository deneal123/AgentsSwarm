"""
HTTP Request/Response Logging Middleware.

Для каждого запроса:
  - Генерирует X-Request-ID (uuid4), если клиент не прислал свой
  - Привязывает structlog contextvars: request_id, method, path
    → все log-вызовы внутри обработчика автоматически получат эти поля
  - После ответа логирует итоговую строку:
    method, path, status_code, duration_ms, trace_id, user_id, request_id, client
  - Добавляет в ответ заголовки X-Request-ID и X-Trace-ID (если трассировка активна)

Пути из SKIP_PATHS (health, metrics) пропускаются без логирования — иначе
Prometheus-скрапер и liveness-проба генерируют тысячи бесполезных строк.

Зависимость structlog.contextvars.bind_contextvars(user_id=...) вызывается
в gateway_service.auth.middleware при валидации JWT, поэтому user_id автоматически
попадёт в итоговую строку "http.request" через механизм merge_contextvars.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)


# ─── OTel helper ─────────────────────────────────────────────────────────────

def get_trace_id() -> str | None:
    """
    Извлечь текущий trace_id из OpenTelemetry span (32 hex-символа).
    Возвращает None если OTel не инициализирован или span невалиден.
    """
    try:
        from opentelemetry import trace  # noqa: PLC0415
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx.is_valid:
            return format(ctx.trace_id, "032x")
    except Exception:
        pass
    return None


# ─── Middleware ───────────────────────────────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Starlette BaseHTTPMiddleware: структурированное логирование HTTP.

    Конфигурация при добавлении:
        app.add_middleware(
            RequestLoggingMiddleware,
            skip_paths={"/health", "/ready", "/metrics"},
        )
    """

    DEFAULT_SKIP_PATHS: frozenset[str] = frozenset({
        "/health",
        "/ready",
        "/metrics",
        "/favicon.ico",
        "/openapi.json",
    })

    def __init__(
        self,
        app: ASGIApp,
        skip_paths: frozenset[str] | set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self._skip = (
            frozenset(skip_paths)
            if skip_paths is not None
            else self.DEFAULT_SKIP_PATHS
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Coroutine[Any, Any, Response]],
    ) -> Response:
        # Пропускаем служебные пути без логирования
        if request.url.path in self._skip:
            return await call_next(request)

        # ── Request-ID ────────────────────────────────────────────────────────
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # ── structlog contextvars ─────────────────────────────────────────────
        # Очищаем контекст от предыдущего запроса (если воркер переиспользуется)
        # и привязываем базовые поля. auth.middleware позже добавит user_id + role.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            http_method=request.method,
            http_path=request.url.path,
        )

        # ── Обработка ────────────────────────────────────────────────────────
        start = time.perf_counter()
        status_code = 500
        response: Response | None = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            trace_id = get_trace_id()

            # user_id доступен через structlog contextvars, привязанный в auth dep,
            # но для явности также читаем из request.state (если auth dep выставил его)
            user_id: str | None = getattr(request.state, "user_id", None)

            # Уровень лога: 5xx → error, 4xx → warning, остальное → info
            if status_code >= 500:
                log_fn = logger.error
            elif status_code >= 400:
                log_fn = logger.warning
            else:
                log_fn = logger.info

            log_fn(
                "http.request",
                status_code=status_code,
                duration_ms=duration_ms,
                trace_id=trace_id,
                # user_id уже в contextvars — дублируем для удобства поиска
                user_id_hint=user_id[:8] + "…" if user_id else None,
                client_ip=request.client.host if request.client else None,
            )

            # ── Диагностические заголовки ────────────────────────────────────
            if response is not None:
                response.headers["X-Request-ID"] = request_id
                if trace_id:
                    response.headers["X-Trace-ID"] = trace_id

            # Сбрасываем контекст после завершения запроса
            structlog.contextvars.clear_contextvars()
