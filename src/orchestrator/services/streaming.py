"""Lightweight StreamCollector scaffold for task-scoped events.

This will later be wired to WebSocket/Gateway. For now, it aggregates events
in memory and mirrors messages into TaskStore logs for compatibility with the
existing `/task/{id}/logs` endpoint.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from orchestrator.services.tasks import TaskStore


class StreamEvent(BaseModel):
    task_id: str
    source: str = Field(..., description="Emitter identifier (agent/tool/server)")
    message: str
    level: str = Field(default="info")
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meta: Dict[str, Any] = Field(default_factory=dict)


class StreamCollector:
    def __init__(self, task_store: Optional[TaskStore] = None, max_events_per_task: int = 500) -> None:
        # deque with maxlen gives O(1) append and automatic eviction of oldest events.
        self._events: Dict[str, Deque[Tuple[int, StreamEvent]]] = {}
        self._seq: Dict[str, int] = {}
        self._task_store = task_store or TaskStore()
        self._max = max_events_per_task

    def record(self, event: StreamEvent) -> int:
        seq = self._seq.get(event.task_id, 0) + 1
        self._seq[event.task_id] = seq

        if event.task_id not in self._events:
            self._events[event.task_id] = deque(maxlen=self._max)
        self._events[event.task_id].append((seq, event))

        # Mirror to task log for existing API consumers
        if self._task_store.exists(event.task_id):
            log_line = f"[{event.level}] {event.source}: {event.message}"
            self._task_store.append_log(event.task_id, log_line)

        return seq

    def get_events(self, task_id: str) -> List[StreamEvent]:
        return [ev for _, ev in self._events.get(task_id, [])]

    def get_since(self, task_id: str, after_seq: int = 0) -> Tuple[List[StreamEvent], int]:
        items = self._events.get(task_id, [])
        filtered = [(seq, ev) for seq, ev in items if seq > after_seq]
        last_seq = filtered[-1][0] if filtered else after_seq
        return [ev for _, ev in filtered], last_seq

    def as_payload(self, task_id: str, after_seq: int = 0) -> Dict[str, Any]:
        events, last_seq = self.get_since(task_id, after_seq)
        return {
            "task_id": task_id,
            "last_seq": last_seq,
            "events": [self._format_event(ev) for ev in events],
        }

    def _format_event(self, ev: StreamEvent) -> Dict[str, Any]:
        return {
            "task_id": ev.task_id,
            "source": ev.source,
            "message": ev.message,
            "level": ev.level,
            "ts": ev.ts.isoformat(),
            "meta": ev.meta,
        }


__all__ = ["StreamCollector", "StreamEvent"]
