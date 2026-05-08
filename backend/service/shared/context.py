from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CorrelationContext:
    correlation_id: str | None = None
    trace_id: str | None = None


_correlation_context: ContextVar[CorrelationContext] = ContextVar(
    "correlation_context", default=CorrelationContext()
)


def set_correlation_context(correlation_id: str | None, trace_id: str | None) -> None:
    _correlation_context.set(CorrelationContext(correlation_id=correlation_id, trace_id=trace_id))


def get_correlation_id() -> str | None:
    return _correlation_context.get().correlation_id


def get_trace_id() -> str | None:
    return _correlation_context.get().trace_id
