from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from orchestrator.services.tasks import TaskInfo, TaskStatus


class TaskRequest(BaseModel):
    prompt: str = Field(..., description="Natural language instruction for the agent layer")
    task_id: Optional[str] = Field(default=None, description="Optional externally provided task identifier")
    session_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Opaque session context from upstream worker/gateway"
    )


class TaskResponse(BaseModel):
    status: str
    task_id: str


class TaskStatusResponse(BaseModel):
    task: TaskInfo


class TaskPlanResponse(BaseModel):
    task_id: str
    plan: list[dict]


class TaskLogsResponse(BaseModel):
    task_id: str
    logs: list[str]


class StreamEventPayload(BaseModel):
    task_id: str
    source: str
    message: str
    level: str
    ts: str
    meta: Dict[str, Any]


class StreamEventsResponse(BaseModel):
    task_id: str
    last_seq: int
    events: List[StreamEventPayload]


class StreamEventIn(BaseModel):
    source: str
    message: str
    level: str = Field(default="info")
    ts: Optional[datetime] = Field(default=None, description="Optional timestamp override")
    meta: Dict[str, Any] = Field(default_factory=dict)
    status: Optional[TaskStatus] = Field(default=None, description="Optional task status update")
    plan_step_id: Optional[int] = Field(default=None, description="Optional plan step id to update")
    append_log: bool = Field(default=False, description="Whether to append message to task logs")


class StreamEventAck(BaseModel):
    task_id: str
    seq: int
    status: TaskStatus


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
