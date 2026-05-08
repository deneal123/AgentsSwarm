from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, WebSocket, status

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

_404 = {404: {"description": "Task not found"}}
_409 = {409: {"description": "Task is in a terminal state and cannot be modified"}}
_422 = {422: {"description": "Validation error in request body"}}


def register_task_routes(
    app: FastAPI,
    task_store: TaskStore,
    stream_collector: StreamCollector,
    runtime: OrchestratorRuntime,
    task_app_service: TaskApplicationService,
) -> None:
    ws_stream_service = WebSocketTaskStreamService(task_store=task_store, stream_collector=stream_collector)

    # ── Status ──────────────────────────────────────────────────────────────

    @app.get(
        "/task/{task_id}/status",
        response_model=TaskStatusResponse,
        tags=["Tasks"],
        summary="Get task status",
        description="Return the current status, prompt, plan, and log of the task.",
        responses={**_404},
    )
    async def get_status(task_id: str) -> TaskStatusResponse:
        return TaskStatusResponse(task=runtime.get_task_or_404(task_id))

    # ── Plan ────────────────────────────────────────────────────────────────

    @app.get(
        "/task/{task_id}/plan",
        response_model=TaskPlanResponse,
        tags=["Tasks"],
        summary="Get execution plan",
        description=(
            "Return the decomposed execution plan with all steps, assigned agents, "
            "and their current statuses: pending | running | completed | failed | canceled."
        ),
        responses={**_404},
    )
    async def get_plan(task_id: str) -> TaskPlanResponse:
        task = runtime.get_task_or_404(task_id)
        return TaskPlanResponse(task_id=task_id, plan=task.plan)

    # ── Logs ────────────────────────────────────────────────────────────────

    @app.get(
        "/task/{task_id}/logs",
        response_model=TaskLogsResponse,
        tags=["Tasks"],
        summary="Get task logs",
        description="Return the ordered list of human-readable log messages appended during task execution.",
        responses={**_404},
    )
    async def get_logs(task_id: str) -> TaskLogsResponse:
        task = runtime.get_task_or_404(task_id)
        return TaskLogsResponse(task_id=task_id, logs=task.logs)

    # ── Cancel ──────────────────────────────────────────────────────────────

    @app.post(
        "/task/{task_id}/cancel",
        response_model=TaskResponse,
        tags=["Tasks"],
        summary="Cancel a running task",
        description=(
            "Request a clean cancellation. All in-progress plan steps are marked `canceled` "
            "and execution stops. Returns immediately; transition happens asynchronously."
        ),
        responses={**_404, **_409},
    )
    async def cancel(task_id: str) -> TaskResponse:
        status_value = task_app_service.cancel_task(task_id)
        logger.info("Task %s canceled", task_id)
        return TaskResponse(status=status_value, task_id=task_id)

    # ── Events (poll) ───────────────────────────────────────────────────────

    @app.get(
        "/task/{task_id}/events",
        response_model=StreamEventsResponse,
        tags=["Events"],
        summary="Poll task events",
        description=(
            "Return all stream events with `seq > after_seq`. "
            "Use `last_seq` from the response as `after_seq` on the next request to receive only new events. "
            "Suitable for long-polling clients that cannot use WebSocket."
        ),
        responses={**_404},
    )
    async def get_events(task_id: str, after_seq: int = 0) -> StreamEventsResponse:
        runtime.get_task_or_404(task_id)
        payload = stream_collector.as_payload(task_id, after_seq=after_seq)
        return StreamEventsResponse(**payload)

    # ── Events (push) ───────────────────────────────────────────────────────

    @app.post(
        "/task/{task_id}/events",
        response_model=StreamEventAck,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["Events"],
        summary="Push an external event",
        description=(
            "Ingest an event from an external worker or MCP server into a task's stream. "
            "Optionally update the task status or a specific plan step. "
            "The event is immediately available to WebSocket and polling subscribers."
        ),
        responses={**_404, **_422},
    )
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

    # ── WebSocket ────────────────────────────────────────────────────────────

    @app.websocket("/ws/task/{task_id}")
    async def task_events_ws(websocket: WebSocket, task_id: str):
        """
        WebSocket stream for real-time task events.

        Connect to receive all events as they are emitted. Each message is a JSON
        object matching the StreamEventPayload schema. Special events:

        - ``meta.type == "route_images"``      — base64-encoded PNG route visualizations from MapAnalyst
        - ``meta.type == "map_image"``          — annotated map with robot position markers
        - ``meta.event_type == "mission_complete"`` — background mission polling result
        - ``meta.code == "task_result"``        — final user-facing orchestrator answer
        - ``meta.code == "step_failed"``        — plan step error with user-facing message
        """
        await ws_stream_service.stream_task_events(websocket=websocket, task_id=task_id)

    # ── Run ──────────────────────────────────────────────────────────────────

    @app.post(
        "/task/{task_id}/run",
        response_model=TaskResponse,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["Tasks"],
        summary="Start a deferred task",
        description=(
            "Trigger execution of a task created with `?run=false` or currently in `pending` state. "
            "Execution runs in the background; subscribe to `/ws/task/{id}` or poll `/task/{id}/events` "
            "for progress updates."
        ),
        responses={**_404, **_409},
    )
    async def run_task(task_id: str, background_tasks: BackgroundTasks) -> TaskResponse:
        task_app_service.ensure_runnable_task(task_id)
        task = runtime.get_task_or_404(task_id)
        task_app_service.schedule_run(task_id, task.prompt, background_tasks)
        return TaskResponse(status=task.status.value, task_id=task_id)

    # ── Replan ───────────────────────────────────────────────────────────────

    @app.post(
        "/task/{task_id}/replan",
        response_model=TaskResponse,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["Tasks"],
        summary="Rebuild and optionally restart the plan",
        description=(
            "Discard the current execution plan and build a new one from the original prompt. "
            "Pass `?run=true` to immediately start execution after replanning. "
            "Useful after transient failures or when external conditions have changed."
        ),
        responses={**_404},
    )
    async def replan_task(
        task_id: str,
        run: bool = False,
        background_tasks: BackgroundTasks = BackgroundTasks(),
    ) -> TaskResponse:
        task_status = await task_app_service.replan_task(task_id)
        if run:
            task = runtime.get_task_or_404(task_id)
            task_app_service.schedule_run(task_id, task.prompt, background_tasks)
        return TaskResponse(status=task_status, task_id=task_id)


__all__ = ["register_task_routes"]
