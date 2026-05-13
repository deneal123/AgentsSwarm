from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CorrelationContext:
    correlation_id: str | None = None
    trace_id: str | None = None


_correlation_context: ContextVar[CorrelationContext | None] = ContextVar(
    "correlation_context", default=None
)


def set_correlation_context(correlation_id: str | None, trace_id: str | None) -> None:
    _correlation_context.set(CorrelationContext(correlation_id=correlation_id, trace_id=trace_id))


def get_correlation_id() -> str | None:
    ctx = _correlation_context.get()
    return ctx.correlation_id if ctx is not None else None


def get_trace_id() -> str | None:
    ctx = _correlation_context.get()
    return ctx.trace_id if ctx is not None else None
