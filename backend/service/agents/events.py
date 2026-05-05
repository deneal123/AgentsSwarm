"""Event protocol for unified agent streaming system."""
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, model_serializer


LEGACY_GUARDRIALS_KEY = "guardrials"
GUARDRAILS_KEY = "guardrails"


def _add_legacy_guardrials_key(metadata: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        return metadata
    if GUARDRAILS_KEY not in metadata:
        return metadata
    if LEGACY_GUARDRIALS_KEY in metadata:
        return metadata
    return {
        **metadata,
        LEGACY_GUARDRIALS_KEY: metadata[GUARDRAILS_KEY],
    }


class EventType(str, Enum):
    """Types of events emitted by agent system."""

    ROUTING_START = "routing_start"
    ROUTING_COMPLETE = "routing_complete"

    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"

    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_COMPLETE = "tool_call_complete"
    TOOL_CALL_ERROR = "tool_call_error"

    STREAM_CHUNK = "stream_chunk"
    STREAM_COMPLETE = "stream_complete"

    STRUCTURED_OUTPUT = "structured_output"

    STATUS_UPDATE = "status_update"

    ERROR = "error"


class AgentEvent(BaseModel):
    """Unified event structure for agent system.

    All agents emit these events which are serialized to WebSocket.
    """

    type: EventType = Field(..., description="Event type")
    agent_name: Optional[str] = Field(None, description="Name of the agent emitting this event")
    data: Any = Field(None, description="Event payload (can be string, dict, list, etc)")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    seq: int = Field(0, description="Sequence number for ordering")

    @model_serializer(mode="wrap")
    def serialize_with_legacy_guardrials(self, handler):
        payload = handler(self)
        payload["metadata"] = _add_legacy_guardrials_key(payload.get("metadata") or {})
        return payload

    class Config:
        use_enum_values = True
