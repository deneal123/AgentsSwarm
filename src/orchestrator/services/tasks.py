"""Lightweight in-memory task tracker used by the HTTP surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


_TERMINAL_STATUSES = {
    TaskStatus.CANCELED.value,
    TaskStatus.COMPLETED.value,
    TaskStatus.FAILED.value,
}


@dataclass
class TaskInfo:
    task_id: str
    prompt: str
    status: TaskStatus = TaskStatus.PENDING
    session_data: Dict[str, Any] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)
    plan: list[Dict[str, Any]] = field(default_factory=list)


class TaskStore:
    """Naive in-memory store. Swap with DB/Redis later."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskInfo] = {}

    def exists(self, task_id: str) -> bool:
        return task_id in self._tasks

    def create_task(self, task_id: str, prompt: str, session_data: Dict[str, Any]) -> TaskInfo:
        task = TaskInfo(task_id=task_id, prompt=prompt, session_data=session_data)
        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        return self._tasks.get(task_id)

    def update_status(self, task_id: str, status: TaskStatus) -> Optional[TaskInfo]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        task.status = status
        return task

    def append_log(self, task_id: str, message: str) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.logs.append(message)

    def set_plan(self, task_id: str, plan: list[Dict[str, Any]]) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.plan = plan

    def update_plan_step(self, task_id: str, step_id: int, status: str) -> None:
        task = self._tasks.get(task_id)
        if not task:
            return
        for step in task.plan:
            if step.get("id") == step_id:
                step["status"] = status
                return

    def cancel_incomplete_steps(self, task_id: str, include_completed: bool = False) -> None:
        """Mark non-terminal plan steps as canceled.

        When include_completed=True, overwrites even already-terminal steps.
        Safe to call when no plan is present.
        """
        task = self._tasks.get(task_id)
        if not task or not task.plan:
            return
        for step in task.plan:
            if include_completed or step.get("status") not in _TERMINAL_STATUSES:
                step["status"] = TaskStatus.CANCELED.value
