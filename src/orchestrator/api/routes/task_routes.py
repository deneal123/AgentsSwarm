from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, HTTPException, WebSocket, status

from orchestrator.api.schemas import (
    StreamEventAck,
    StreamEventIn,
    StreamEventsResponse,
    TaskLogsResponse,
    TaskPlanResponse,
    TaskResponse,
    TaskStatusResponse,
)
from orchestrator.services.orchestrator_runtime import OrchestratorRuntime
from orchestrator.services.streaming import StreamCollector
from orchestrator.services.task_application_service import IngestEventCommand, TaskApplicationService
from orchestrator.services.tasks import TaskStore
from orchestrator.services.websocket_stream import WebSocketTaskStreamService
from orchestrator.utils.logger import get_logger


logger = get_logger(__name__)


def register_task_routes(
    app: FastAPI,
    task_store: TaskStore,
    stream_collector: StreamCollector,
    runtime: OrchestratorRuntime,
    task_app_service: TaskApplicationService,
) -> None:
    ws_stream_service = WebSocketTaskStreamService(task_store=task_store, stream_collector=stream_collector)

    @app.get("/task/{task_id}/status", response_model=TaskStatusResponse)
    async def get_status(task_id: str) -> TaskStatusResponse:
        return TaskStatusResponse(task=runtime.get_task_or_404(task_id))

    @app.get("/task/{task_id}/plan", response_model=TaskPlanResponse)
    async def get_plan(task_id: str) -> TaskPlanResponse:
        task = runtime.get_task_or_404(task_id)
        return TaskPlanResponse(task_id=task_id, plan=task.plan)

    @app.get("/task/{task_id}/logs", response_model=TaskLogsResponse)
    async def get_logs(task_id: str) -> TaskLogsResponse:
        task = runtime.get_task_or_404(task_id)
        return TaskLogsResponse(task_id=task_id, logs=task.logs)

    @app.post("/task/{task_id}/cancel", response_model=TaskResponse)
    async def cancel(task_id: str) -> TaskResponse:
        status_value = task_app_service.cancel_task(task_id)
        logger.info("Task %s canceled", task_id)
        return TaskResponse(status=status_value, task_id=task_id)

    @app.get("/task/{task_id}/events", response_model=StreamEventsResponse)
    async def get_events(task_id: str, after_seq: int = 0) -> StreamEventsResponse:
        runtime.get_task_or_404(task_id)
        payload = stream_collector.as_payload(task_id, after_seq=after_seq)
        return StreamEventsResponse(**payload)

    @app.post("/task/{task_id}/events", response_model=StreamEventAck, status_code=status.HTTP_202_ACCEPTED)
    async def ingest_event(task_id: str, event: StreamEventIn) -> StreamEventAck:
        ingest_result = task_app_service.ingest_event(
            IngestEventCommand(
                task_id=task_id,
                source=event.source,
                message=event.message,
                level=event.level,
                ts=event.ts,
                meta=event.meta,
                event_status=event.status,
                plan_step_id=event.plan_step_id,
                append_log=event.append_log,
            )
        )
        return StreamEventAck(task_id=task_id, seq=ingest_result.seq, status=ingest_result.status)

    @app.websocket("/ws/task/{task_id}")
    async def task_events_ws(websocket: WebSocket, task_id: str):
        await ws_stream_service.stream_task_events(websocket=websocket, task_id=task_id)

    @app.post("/task/{task_id}/run", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
    async def run_task(task_id: str, background_tasks: BackgroundTasks) -> TaskResponse:
        task_app_service.ensure_runnable_task(task_id)
        task = runtime.get_task_or_404(task_id)
        task_app_service.schedule_run(task_id, task.prompt, background_tasks)
        return TaskResponse(status=task.status.value, task_id=task_id)

    @app.post("/task/{task_id}/replan", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
    async def replan_task(task_id: str, run: bool = False, background_tasks: BackgroundTasks = BackgroundTasks()) -> TaskResponse:
        task_status = task_app_service.replan_task(task_id)

        if run:
            task = runtime.get_task_or_404(task_id)
            task_app_service.schedule_run(task_id, task.prompt, background_tasks)
        return TaskResponse(status=task_status, task_id=task_id)


__all__ = ["register_task_routes"]
