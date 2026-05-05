from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from orchestrator.services.orchestrator_runtime import OrchestratorRuntime
from orchestrator.services.streaming import StreamCollector, StreamEvent
from orchestrator.services.tasks import TaskStatus, TaskStore


@dataclass(frozen=True)
class IngestEventCommand:
    task_id: str
    source: str
    message: str
    level: str
    ts: datetime | None
    meta: Dict[str, Any]
    event_status: TaskStatus | None
    plan_step_id: int | None
    append_log: bool


@dataclass(frozen=True)
class IngestEventResult:
    seq: int
    status: TaskStatus


class TaskEventIngestionService:
    def __init__(
        self,
        task_store: TaskStore,
        stream_collector: StreamCollector,
        runtime: OrchestratorRuntime,
    ) -> None:
        self._task_store = task_store
        self._stream_collector = stream_collector
        self._runtime = runtime

    def ingest_event(self, command: IngestEventCommand) -> IngestEventResult:
        task_id = command.task_id
        self._runtime.get_task_or_404(task_id)

        seq = self._stream_collector.record(
            StreamEvent(
                task_id=task_id,
                source=command.source,
                message=command.message,
                level=command.level,
                ts=command.ts or datetime.now(timezone.utc),
                meta=command.meta,
            )
        )

        if command.event_status:
            self._apply_status(task_id, command)

        if command.plan_step_id is not None:
            step_status = command.event_status.value if command.event_status else TaskStatus.RUNNING.value
            self._task_store.update_plan_step(task_id, command.plan_step_id, step_status)

        if command.append_log:
            self._task_store.append_log(
                task_id, f"[{command.level}] {command.source}: {command.message}"
            )

        updated_task = self._task_store.get_task(task_id)
        return IngestEventResult(
            seq=seq,
            status=updated_task.status if updated_task else TaskStatus.PENDING,
        )

    def _apply_status(self, task_id: str, command: IngestEventCommand) -> None:
        event_status = command.event_status
        assert event_status is not None

        if event_status == TaskStatus.FAILED:
            self._task_store.update_status(task_id, TaskStatus.FAILED)
            self._task_store.cancel_incomplete_steps(task_id, include_completed=True)
            self._runtime.record_user_error(
                task_id,
                message="В задаче произошла ошибка. Пожалуйста, повторите или обратитесь к оператору.",
                code="task_failed",
                detail=command.message,
            )
        elif event_status == TaskStatus.COMPLETED:
            # Only mark completed when the full plan is done; ignore premature signals.
            task = self._task_store.get_task(task_id)
            task_plan = task.plan if task else []
            if not task_plan or all(
                step.get("status") == TaskStatus.COMPLETED.value for step in task_plan
            ):
                self._task_store.update_status(task_id, TaskStatus.COMPLETED)
        else:
            self._task_store.update_status(task_id, event_status)


__all__ = ["IngestEventCommand", "IngestEventResult", "TaskEventIngestionService"]
