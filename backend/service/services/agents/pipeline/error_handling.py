"""Error handling helpers for agent pipeline."""

from __future__ import annotations

from service.services.agents.domain.events import AgentEvent, EventType


def build_processing_error_event(exc: Exception, *, thread_id: str, logger) -> AgentEvent:
    """Create standardized processing error event and log the exception."""
    logger.exception("Error in agent processing")
    return AgentEvent(
        type=EventType.ERROR,
        data=str(exc),
        metadata={"error_type": type(exc).__name__, "thread_id": thread_id},
    )
