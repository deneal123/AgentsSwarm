"""FastAPI application setup for the Orchestrator service.

This module wires the HTTP API surface (health, task lifecycle) and exposes a
singleton FastAPI app instance. Agent execution, streaming, and MCP integration
will be layered on top of this skeleton.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from orchestrator.config import settings
from orchestrator.services.sessions import SessionManager, get_session_manager
from orchestrator.services.planner import PlanStep, build_plan
from orchestrator.services.streaming import StreamCollector, StreamEvent
from orchestrator.services.tasks import TaskInfo, TaskStatus, TaskStore, get_task_store
from orchestrator.utils.logger import get_logger

logger = get_logger(__name__)


class TaskRequest(BaseModel):
    prompt: str = Field(..., description="Natural language instruction for the agent layer")
    task_id: Optional[str] = Field(
        default=None, description="Optional externally provided task identifier"
    )
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


class StreamEventAck(BaseModel):
    task_id: str
    seq: int
    status: TaskStatus


def create_app(
    task_store: Annotated[TaskStore, Depends(get_task_store)] | None = None,
    session_manager: Annotated[SessionManager, Depends(get_session_manager)] | None = None,
    stream_collector: StreamCollector | None = None,
) -> FastAPI:
    ts = task_store or TaskStore()
    sm = session_manager or SessionManager()
    sc = stream_collector or StreamCollector(task_store=ts)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Starting Orchestrator service")
        await sm.connect()
        yield
        logger.info("Stopping Orchestrator service")
        await sm.close()

    app = FastAPI(
        title="Orchestrator",
        version=str(settings.get("version", "0.0.1")),
        description="Agentic orchestrator for robot swarm control",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "version": str(settings.get("version", "0.0.1")),
                "env": os.getenv("ENV", "dev"),
                "redis": {"status": sm.status},
            }
        )

    @app.post("/task", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
    async def submit_task(
        request: TaskRequest,
        run: bool = True,
        background_tasks: BackgroundTasks = None,
    ) -> TaskResponse:
        task_id = request.task_id or uuid4().hex
        if ts.exists(task_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Task with id {task_id} already exists",
            )

        ts.create_task(task_id, request.prompt, request.session_data or {})
        await sm.update_session(task_id, request.session_data or {})
        logger.info("Task %s accepted", task_id)
        sc.record(
            StreamEvent(
                task_id=task_id,
                source="api",
                message="Task accepted",
                level="info",
                meta={"prompt_len": len(request.prompt)},
            )
        )
        if run:
            background_tasks.add_task(_run_task, task_id, request.prompt)
            current = ts.get_task(task_id)
            return TaskResponse(status=current.status.value if current else TaskStatus.PENDING.value, task_id=task_id)
        return TaskResponse(status=TaskStatus.PENDING.value, task_id=task_id)

    @app.get("/task/{task_id}/status", response_model=TaskStatusResponse)
    async def get_status(task_id: str) -> TaskStatusResponse:
        task = ts.get_task(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return TaskStatusResponse(task=task)

    @app.get("/task/{task_id}/plan", response_model=TaskPlanResponse)
    async def get_plan(task_id: str) -> TaskPlanResponse:
        task = ts.get_task(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return TaskPlanResponse(task_id=task_id, plan=task.plan)

    @app.get("/task/{task_id}/logs", response_model=TaskLogsResponse)
    async def get_logs(task_id: str) -> TaskLogsResponse:
        task = ts.get_task(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return TaskLogsResponse(task_id=task_id, logs=task.logs)

    @app.post("/task/{task_id}/cancel", response_model=TaskResponse)
    async def cancel(task_id: str) -> TaskResponse:
        existing = ts.get_task(task_id)
        prev_status = existing.status if existing else None
        updated = ts.update_status(task_id, TaskStatus.CANCELED)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        ts.cancel_incomplete_steps(task_id)
        sc.record(
            StreamEvent(
                task_id=task_id,
                source="orchestrator",
                message="Task canceled",
                level="warning",
                meta={},
            )
        )
        sc.record(
            StreamEvent(
                task_id=task_id,
                source="orchestrator",
                message="Task canceled during execution",
                level="warning",
                meta={"prev_status": prev_status.value if prev_status else None},
            )
        )
        logger.info("Task %s canceled", task_id)
        return TaskResponse(status=TaskStatus.CANCELED.value, task_id=task_id)

    @app.get("/task/{task_id}/events", response_model=StreamEventsResponse)
    async def get_events(task_id: str, after_seq: int = 0) -> StreamEventsResponse:
        task = ts.get_task(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        payload = sc.as_payload(task_id, after_seq=after_seq)
        return StreamEventsResponse(**payload)

    @app.post("/task/{task_id}/events", response_model=StreamEventAck, status_code=status.HTTP_202_ACCEPTED)
    async def ingest_event(task_id: str, event: StreamEventIn) -> StreamEventAck:
        task = ts.get_task(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        stream_event = StreamEvent(
            task_id=task_id,
            source=event.source,
            message=event.message,
            level=event.level,
            ts=event.ts or datetime.now(timezone.utc),
            meta=event.meta,
        )
        seq = sc.record(stream_event)

        if event.status:
            ts.update_status(task_id, event.status)

        updated_task = ts.get_task(task_id)
        return StreamEventAck(task_id=task_id, seq=seq, status=updated_task.status if updated_task else TaskStatus.PENDING)

    @app.post("/task/{task_id}/run", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
    async def run_task(task_id: str, background_tasks: BackgroundTasks = None) -> TaskResponse:
        task = ts.get_task(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        if task.status == TaskStatus.RUNNING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task already running")
        if task.status in {TaskStatus.CANCELED, TaskStatus.COMPLETED}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task not runnable")
        background_tasks.add_task(_run_task, task_id, task.prompt)
        updated = ts.get_task(task_id)
        return TaskResponse(status=updated.status.value if updated else TaskStatus.PENDING.value, task_id=task_id)

    @app.exception_handler(Exception)
    async def _unhandled_exc(request: Request, exc: Exception):
        task_ctx = request.path_params.get("task_id") if hasattr(request, "path_params") else None
        logger.exception(
            "Unhandled error",
            extra={"path": request.url.path, "task_id": task_ctx},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    async def _run_task(task_id: str, prompt: str) -> None:
        existing = ts.get_task(task_id)
        if existing and existing.status == TaskStatus.CANCELED:
            ts.cancel_incomplete_steps(task_id)
            sc.record(
                StreamEvent(
                    task_id=task_id,
                    source="orchestrator",
                    message="Task canceled before start",
                    level="warning",
                    meta={},
                )
            )
            return

        ts.update_status(task_id, TaskStatus.RUNNING)
        plan = build_plan(prompt)
        ts.set_plan(task_id, [step.as_dict() for step in plan])
        sc.record(
            StreamEvent(
                task_id=task_id,
                source="planner",
                message="Plan created",
                level="info",
                meta={"steps": [s.as_dict() for s in plan]},
            )
        )
        sc.record(
            StreamEvent(
                task_id=task_id,
                source="orchestrator",
                message="Processing started",
                level="info",
                meta={"prompt": prompt[:80]},
            )
        )
        try:
            # Small delay to allow early cancellation before executing steps
            await asyncio.sleep(0.05)

            def _is_canceled() -> bool:
                task = ts.get_task(task_id)
                return bool(task and task.status == TaskStatus.CANCELED)

            for step in plan:
                if _is_canceled():
                    ts.cancel_incomplete_steps(task_id)
                    sc.record(
                        StreamEvent(
                            task_id=task_id,
                            source="orchestrator",
                            message="Task canceled during execution",
                            level="warning",
                            meta={},
                        )
                    )
                    break

                ts.update_plan_step(task_id, step.id, "running")
                sc.record(
                    StreamEvent(
                        task_id=task_id,
                        source="planner",
                        message=f"Plan step {step.id} started: {step.description}",
                        level="info",
                        meta={"agent": step.agent},
                    )
                )
                await asyncio.sleep(0.1)

                if _is_canceled():
                    ts.update_plan_step(task_id, step.id, TaskStatus.CANCELED.value)
                    ts.cancel_incomplete_steps(task_id)
                    sc.record(
                        StreamEvent(
                            task_id=task_id,
                            source="orchestrator",
                            message="Task canceled during execution",
                            level="warning",
                            meta={},
                        )
                    )
                    break

                ts.update_plan_step(task_id, step.id, "completed")
                sc.record(
                    StreamEvent(
                        task_id=task_id,
                        source="planner",
                        message=f"Plan step {step.id} completed",
                        level="info",
                        meta={"agent": step.agent},
                    )
                )

            else:
                current = ts.get_task(task_id)
                if current and current.status != TaskStatus.CANCELED:
                    sc.record(
                        StreamEvent(
                            task_id=task_id,
                            source="agent",
                            message="Task completed",
                            level="info",
                            meta={"steps": len(plan)},
                        )
                    )
                    ts.update_status(task_id, TaskStatus.COMPLETED)
        except Exception as exc:  # pragma: no cover - defensive
            ts.update_status(task_id, TaskStatus.FAILED)
            sc.record(
                StreamEvent(
                    task_id=task_id,
                    source="orchestrator",
                    message=f"Task failed: {exc}",
                    level="error",
                    meta={},
                )
            )

    return app


# Expose a module-level app for uvicorn (`uvicorn orchestrator.app:app`)
app = create_app()
