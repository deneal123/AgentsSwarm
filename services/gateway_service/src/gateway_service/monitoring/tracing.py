"""
OpenTelemetry tracing setup для Gateway Service.

Возможности:
  - OTLP gRPC экспортер (Jaeger / Tempo / любой OTel Collector)
  - W3C TraceContext propagation (заголовки traceparent / tracestate)
  - TraceIdRatioBased sampling (sample_rate < 1.0) или ALWAYS_ON (= 1.0)
  - FastAPIInstrumentor — авто-инструментация всех HTTP-маршрутов
  - get_trace_id() — публичный хелпер для логирования и заголовков ответа

Все импорты opentelemetry завёрнуты в try/except ImportError —
если пакеты не установлены, трассировка просто отключается (fail-open).
"""

from __future__ import annotations

import structlog

from fastapi import FastAPI

logger = structlog.get_logger(__name__)


def get_trace_id() -> str | None:
    """
    Вернуть текущий trace_id (32-символьная hex-строка) из активного OTel span.
    Возвращает None если трассировка не настроена или span невалиден.

    Используется в:
      - middleware/logging.py  → заголовок X-Trace-ID и поле лога trace_id
      - exception_handlers     → поле лога для корреляции ошибок
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


def setup_tracing(
    app: FastAPI,
    endpoint: str,
    sample_rate: float = 1.0,
    service_name: str = "gateway-service",
    service_version: str = "0.1.0",
) -> None:
    """
    Инициализировать OpenTelemetry трассировку.

    Args:
        app:            FastAPI приложение для инструментации
        endpoint:       OTLP gRPC endpoint, напр. "http://jaeger:4317"
        sample_rate:    Доля трассируемых запросов (0.0–1.0). 1.0 = все.
        service_name:   Имя сервиса в Jaeger/Tempo UI
        service_version: Версия для resource атрибута "service.version"
    """
    try:
        from opentelemetry import trace  # noqa: PLC0415
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.propagate import set_global_textmap
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import ALWAYS_ON, TraceIdRatioBased
        from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

        # ── Resource: метаданные сервиса ──────────────────────────────────
        resource = Resource.create({
            "service.name": service_name,
            "service.version": service_version,
        })

        # ── Sampler ───────────────────────────────────────────────────────
        sampler = ALWAYS_ON if sample_rate >= 1.0 else TraceIdRatioBased(sample_rate)

        # ── Provider + Exporter ───────────────────────────────────────────
        provider = TracerProvider(resource=resource, sampler=sampler)
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        # ── Propagation: W3C TraceContext (traceparent / tracestate) ──────
        # Позволяет сквозную трассировку через HTTP-запросы между сервисами
        set_global_textmap(TraceContextTextMapPropagator())

        # ── FastAPI auto-instrumentation ──────────────────────────────────
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)

        logger.info(
            "tracing.initialized",
            endpoint=endpoint,
            sample_rate=sample_rate,
            service=service_name,
        )

    except ImportError:
        logger.warning(
            "opentelemetry.not_available",
            hint="Install opentelemetry-sdk, opentelemetry-exporter-otlp, "
                 "opentelemetry-instrumentation-fastapi",
        )
    except Exception as exc:
        logger.error("tracing.setup_failed", error=str(exc))
