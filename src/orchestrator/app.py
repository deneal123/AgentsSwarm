"""FastAPI application setup for the Orchestrator service.

This module wires the HTTP API surface (health, task lifecycle) and exposes a
singleton FastAPI app instance. Agent execution, streaming, and MCP integration
will be layered on top of this skeleton.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, status
from fastapi.responses import JSONResponse

from orchestrator.api.error_handlers import register_exception_handlers
from orchestrator.api.schemas import (
    TaskRequest,
    TaskResponse,
)
from orchestrator.api.routes import register_task_routes
from orchestrator.config import settings
from orchestrator.services.sessions import SessionManager, get_session_manager
from orchestrator.services.service_container import ServiceContainerFactory
from orchestrator.services.streaming import StreamCollector
from orchestrator.services.tasks import TaskStore, get_task_store
from orchestrator.utils.logger import get_logger

logger = get_logger(__name__)


def create_app(
    task_store: Annotated[TaskStore, Depends(get_task_store)] | None = None,
    session_manager: Annotated[SessionManager, Depends(get_session_manager)] | None = None,
    stream_collector: StreamCollector | None = None,
    enable_debug_routes: bool | None = None,
) -> FastAPI:
    container = ServiceContainerFactory.create(
        task_store=task_store,
        session_manager=session_manager,
        stream_collector=stream_collector,
    )
    ts = container.task_store
    sm = container.session_manager
    sc = container.stream_collector
    runtime = container.runtime
    task_app_service = container.task_app_service

    debug_routes = enable_debug_routes
    if debug_routes is None:
        debug_routes = bool(settings.get("enable_debug_routes", False)) or os.getenv("ENABLE_DEBUG_ROUTES") == "1"

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
        background_tasks: BackgroundTasks,
        run: bool = True,
    ) -> TaskResponse:
        submit_result = await task_app_service.submit_task(
            prompt=request.prompt,
            session_data=request.session_data,
            run=run,
            background_tasks=background_tasks,
            external_task_id=request.task_id,
        )
        logger.info("Task %s accepted", submit_result.task_id)
        return TaskResponse(status=submit_result.status, task_id=submit_result.task_id)

    register_task_routes(
        app=app,
        task_store=ts,
        stream_collector=sc,
        runtime=runtime,
        task_app_service=task_app_service,
    )

    register_exception_handlers(app=app, task_store=ts, runtime=runtime)

    if debug_routes:

        @app.get("/debug/crash/{task_id}")
        async def _crash(task_id: str):
            raise RuntimeError("Debug crash")

    return app


# Expose a module-level app for uvicorn (`uvicorn orchestrator.app:app`)
app = create_app()
