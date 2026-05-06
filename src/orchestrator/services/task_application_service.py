from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import BackgroundTasks, HTTPException, status

from orchestrator.services.orchestrator_runtime import OrchestratorRuntime
from orchestrator.services.sessions import SessionManager
from orchestrator.services.streaming import StreamCollector, StreamEvent
from orchestrator.services.task_event_ingestion_service import IngestEventCommand, IngestEventResult, TaskEventIngestionService
from orchestrator.services.tasks import TaskStatus, TaskStore


@dataclass(frozen=True)
class SubmitTaskResult:
    task_id: str
    status: str


class TaskApplicationService:
    def __init__(
        self,
        task_store: TaskStore,
        session_manager: SessionManager,
        stream_collector: StreamCollector,
        runtime: OrchestratorRuntime,
        event_ingestion_service: TaskEventIngestionService,
    ) -> None:
        self._task_store = task_store
        self._session_manager = session_manager
        self._stream_collector = stream_collector
        self._runtime = runtime
        self._event_ingestion_service = event_ingestion_service

    async def submit_task(
        self,
        prompt: str,
        session_data: Optional[Dict[str, Any]],
        run: bool,
        background_tasks: BackgroundTasks,
        external_task_id: str | None = None,
    ) -> SubmitTaskResult:
        task_id = external_task_id or uuid4().hex
        if self._task_store.exists(task_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Task with id {task_id} already exists",
            )

        data = session_data or {}
        self._task_store.create_task(task_id, prompt, data)
        await self._session_manager.update_session(task_id, data)
        self._stream_collector.record(
            StreamEvent(
                task_id=task_id,
                source="api",
                message="Task accepted",
                level="info",
                meta={"prompt_len": len(prompt)},
            )
        )

        if run:
            background_tasks.add_task(self._runtime.run_task, task_id, prompt)
        current = self._task_store.get_task(task_id)
        current_status = current.status.value if current else TaskStatus.PENDING.value
        status_value = current_status if run else TaskStatus.PENDING.value
        return SubmitTaskResult(task_id=task_id, status=status_value)

    def cancel_task(self, task_id: str) -> str:
        existing = self._task_store.get_task(task_id)
        was_running = existing is not None and existing.status == TaskStatus.RUNNING
        updated = self._task_store.update_status(task_id, TaskStatus.CANCELED)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        self._task_store.cancel_incomplete_steps(task_id, include_completed=True)
        self._stream_collector.record(
            StreamEvent(
                task_id=task_id,
                source="orchestrator",
                message="Task canceled" + (" during execution" if was_running else ""),
                level="warning",
                meta={"was_running": was_running},
            )
        )
        return TaskStatus.CANCELED.value

    def ingest_event(self, command: IngestEventCommand) -> IngestEventResult:
        return self._event_ingestion_service.ingest_event(command)

    def schedule_run(self, task_id: str, prompt: str, background_tasks: BackgroundTasks) -> None:
        background_tasks.add_task(self._runtime.run_task, task_id, prompt)

    async def replan_task(self, task_id: str) -> str:
        task = self._runtime.get_task_or_404(task_id)
        if task.status == TaskStatus.RUNNING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task already running")

        await self._runtime.build_and_store_plan(task_id, task.prompt, message="Plan rebuilt")
        self._task_store.update_status(task_id, TaskStatus.PENDING)
        return TaskStatus.PENDING.value

    def ensure_runnable_task(self, task_id: str) -> None:
        task = self._runtime.get_task_or_404(task_id)
        if task.status == TaskStatus.RUNNING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task already running")
        if task.status in {TaskStatus.CANCELED, TaskStatus.COMPLETED}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task not runnable")


__all__ = [
    "TaskApplicationService",
    "SubmitTaskResult",
    "IngestEventCommand",
    "IngestEventResult",
]
