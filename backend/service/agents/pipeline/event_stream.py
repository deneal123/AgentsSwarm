"""Helpers for sequencing and emitting agent events."""

from __future__ import annotations

from typing import Any, Optional

from service.agents.events import AgentEvent, EventType


class EventSequencer:
    """Assign monotonic sequence numbers to AgentEvent instances."""

    def __init__(self) -> None:
        self._seq = 0

    def attach(self, event: AgentEvent) -> AgentEvent:
        """Attach next seq number to an existing event and return it."""
        self._seq += 1
        event.seq = self._seq
        return event

    def new(
        self,
        *,
        type: EventType,
        agent_name: Optional[str] = None,
        data: Any = None,
        metadata: Optional[dict] = None,
    ) -> AgentEvent:
        """Build and sequence a new event in one call."""
        event = AgentEvent(
            type=type,
            agent_name=agent_name,
            data=data,
            metadata=metadata or {},
        )
        return self.attach(event)
