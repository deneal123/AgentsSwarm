from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from orchestrator.services.tasks import TaskInfo, TaskStatus


class TaskRequest(BaseModel):
    """Incoming request to submit a new task to the orchestrator."""

    prompt: str = Field(
        ...,
        description="Natural language instruction for the agent layer.",
        examples=["Send carter01 to coordinates (10, 12)"],
        min_length=1,
        max_length=4096,
    )
    task_id: Optional[str] = Field(
        default=None,
        description="Optional externally provided task identifier. "
                    "If omitted the orchestrator generates one.",
        examples=["9cf9d2a325ed45eb8ff35b785afda1b5"],
    )
    session_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Opaque session context forwarded from the upstream gateway "
                    "(e.g. last robot_id, conversation history).",
        examples=[{"robot_id": "carter01", "locale": "ru"}],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": "Send carter01 to coordinates (10, 12)",
                "session_data": {"robot_id": "carter01"},
            }
        }
    }


class TaskResponse(BaseModel):
    """Minimal task acknowledgement returned after creating or mutating a task."""

    status: str = Field(description="Current task status.", examples=["pending", "running", "completed"])
    task_id: str = Field(description="Unique task identifier.", examples=["9cf9d2a325ed45eb8ff35b785afda1b5"])

    model_config = {
        "json_schema_extra": {
            "example": {"status": "pending", "task_id": "9cf9d2a325ed45eb8ff35b785afda1b5"}
        }
    }


class TaskStatusResponse(BaseModel):
    """Full task info including status, prompt, plan, and logs."""

    task: TaskInfo


class TaskPlanResponse(BaseModel):
    """Decomposed execution plan for a task."""

    task_id: str = Field(description="Task identifier.", examples=["9cf9d2a325ed45eb8ff35b785afda1b5"])
    plan: list[dict] = Field(
        description="Ordered list of plan steps with agent assignments and statuses."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": "9cf9d2a325ed45eb8ff35b785afda1b5",
                "plan": [
                    {"id": 1, "agent": "MapAnalyst", "description": "Map analysis", "status": "completed"},
                    {"id": 2, "agent": "Navigation", "description": "Move carter01 to (10, 12)", "status": "running"},
                ],
            }
        }
    }


class TaskLogsResponse(BaseModel):
    """Human-readable log lines collected during task execution."""

    task_id: str = Field(description="Task identifier.", examples=["9cf9d2a325ed45eb8ff35b785afda1b5"])
    logs: list[str] = Field(description="Ordered log messages appended during execution.")


class StreamEventPayload(BaseModel):
    """A single streamed event emitted by the orchestrator or an agent."""

    task_id: str = Field(description="Task this event belongs to.")
    source: str = Field(
        description="Emitting component: api | planner | agent | agent-sdk | orchestrator."
    )
    message: str = Field(description="Human-readable event text.")
    level: str = Field(description="Severity level: info | warning | error.")
    ts: str = Field(description="ISO-8601 UTC timestamp.")
    meta: Dict[str, Any] = Field(
        description="Structured metadata. May include event_type, user_facing, code, images."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": "9cf9d2a325ed45eb8ff35b785afda1b5",
                "source": "agent-sdk",
                "message": "✓ Миссия nav_abc123 завершена успешно (COMPLETED).",
                "level": "info",
                "ts": "2026-05-08T09:43:38.000000+00:00",
                "meta": {
                    "event_type": "mission_complete",
                    "mission_id": "nav_abc123",
                    "state": "COMPLETED",
                },
            }
        }
    }


class StreamEventsResponse(BaseModel):
    """Paginated batch of stream events for polling clients."""

    task_id: str = Field(description="Task identifier.")
    last_seq: int = Field(
        description="Sequence number of the last returned event. "
                    "Pass as after_seq on the next poll to receive only new events."
    )
    events: List[StreamEventPayload] = Field(
        description="Events with seq > after_seq, ordered chronologically."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": "9cf9d2a325ed45eb8ff35b785afda1b5",
                "last_seq": 12,
                "events": [],
            }
        }
    }


class StreamEventIn(BaseModel):
    """External event pushed into a task stream by a worker or MCP server."""

    source: str = Field(
        description="Emitting component identifier.",
        examples=["worker", "mission-dispatch"],
    )
    message: str = Field(
        description="Human-readable event text.",
        examples=["Mission nav_abc123 completed"],
    )
    level: str = Field(
        default="info",
        description="Severity level: info | warning | error.",
        examples=["info"],
    )
    ts: Optional[datetime] = Field(
        default=None,
        description="Optional timestamp override (defaults to server time).",
    )
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary structured metadata.",
    )
    status: Optional[TaskStatus] = Field(
        default=None,
        description="If provided, updates the task status.",
        examples=["completed", "failed"],
    )
    plan_step_id: Optional[int] = Field(
        default=None,
        description="If provided, updates the status of this plan step.",
        examples=[2],
    )
    append_log: bool = Field(
        default=False,
        description="Whether to append the message to the task's human-readable log.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "source": "worker",
                "message": "Mission nav_abc123 completed",
                "level": "info",
                "meta": {"mission_id": "nav_abc123"},
                "status": "completed",
            }
        }
    }


class StreamEventAck(BaseModel):
    """Acknowledgement returned after a successful event ingest."""

    task_id: str = Field(description="Task identifier.")
    seq: int = Field(description="Assigned sequence number for the ingested event.")
    status: TaskStatus = Field(description="Current task status after applying the event.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": "9cf9d2a325ed45eb8ff35b785afda1b5",
                "seq": 13,
                "status": "completed",
            }
        }
    }


__all__ = [
    "TaskRequest",
    "TaskResponse",
    "TaskStatusResponse",
    "TaskPlanResponse",
    "TaskLogsResponse",
    "StreamEventPayload",
    "StreamEventsResponse",
    "StreamEventIn",
    "StreamEventAck",
]
