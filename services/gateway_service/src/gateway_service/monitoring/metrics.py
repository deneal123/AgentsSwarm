"""Prometheus metrics для Gateway Service."""

from __future__ import annotations

from fastapi import FastAPI
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

# ─── Метрики ────────────────────────────────────────────────────────────────

http_requests_total = Counter(
    "gateway_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

http_request_duration_seconds = Histogram(
    "gateway_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

ws_connections_active = Gauge(
    "gateway_ws_connections_active",
    "Active WebSocket connections",
    ["channel"],
)

rabbitmq_messages_published = Counter(
    "gateway_rabbitmq_messages_published_total",
    "Messages published to RabbitMQ",
    ["exchange", "routing_key"],
)


def setup_metrics(app: FastAPI) -> None:
    """Регистрирует /metrics эндпоинт и middleware для сбора метрик."""

    async def metrics_endpoint(request: Request) -> Response:
        # Обновляем gauge WS-соединений прямо перед выдачей метрик
        try:
            from gateway_service.ws.manager import get_connection_manager
            mgr = get_connection_manager()
            info = mgr.connection_info()
            # Сбрасываем и пересчитываем по каналам
            for channel in ("chat", "telemetry", "notifications"):
                count = sum(1 for c in info if c["channel"] == channel)
                ws_connections_active.labels(channel=channel).set(count)
        except Exception:
            pass

        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    app.routes.append(
        Route("/metrics", endpoint=metrics_endpoint, methods=["GET"])
    )
