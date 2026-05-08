"""FastAPI application setup for the Orchestrator service."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from orchestrator.api.error_handlers import register_exception_handlers
from orchestrator.api.schemas import TaskRequest, TaskResponse
from orchestrator.api.routes import register_task_routes
from orchestrator.config import settings
from orchestrator.services.sessions import SessionManager
from orchestrator.services.service_container import ServiceContainerFactory
from orchestrator.services.streaming import StreamCollector
from orchestrator.services.tasks import TaskStore
from orchestrator.utils.logger import get_logger

logger = get_logger(__name__)

_OPENAPI_TAGS = [
    {
        "name": "Tasks",
        "description": (
            "Task lifecycle management: create, run, cancel, replan. "
            "A task is a natural-language instruction decomposed into a multi-agent execution plan."
        ),
    },
    {
        "name": "Events",
        "description": (
            "Stream events emitted by agents and the orchestrator. "
            "Use GET for polling or connect via WebSocket (`/ws/task/{id}`) for real-time push."
        ),
    },
    {
        "name": "System",
        "description": "Health check and service metadata.",
    },
]


def create_app(
    task_store: TaskStore | None = None,
    session_manager: SessionManager | None = None,
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
        debug_routes = (
            bool(settings.get("enable_debug_routes", False))
            or os.getenv("ENABLE_DEBUG_ROUTES") == "1"
        )

    _version = str(settings.get("version", "0.0.1"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Starting Orchestrator v%s", _version)
        await sm.connect()
        yield
        logger.info("Stopping Orchestrator")
        await sm.close()

    app = FastAPI(
        title="Orchestrator",
        version=_version,
        description=(
            "Agentic orchestrator for robot swarm control.\n\n"
            "Accepts natural-language prompts, decomposes them into a multi-step plan, "
            "routes each step to a specialised agent (Navigation, SwarmCoordinator, RobotInfo, …), "
            "and streams live events over WebSocket.\n\n"
            "**Key concepts:**\n"
            "- Every request creates a *task* with a unique `task_id`.\n"
            "- The plan is built by an LLM planner and executed step-by-step.\n"
            "- All agent activity (tool calls, mission results, map images) is streamed "
            "in real time via `/ws/task/{id}` or polled via `/task/{id}/events`."
        ),
        openapi_tags=_OPENAPI_TAGS,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Set CORS_ORIGINS env var to a comma-separated list for production.
    # Defaults to "*" (permissive) for local development.
    _cors_origins_raw = os.getenv("CORS_ORIGINS", "*")
    _cors_origins = (
        ["*"]
        if _cors_origins_raw.strip() == "*"
        else [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        # credentials=True is incompatible with allow_origins=["*"]
        allow_credentials=_cors_origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ───────────────────────────────────────────────────────────────

    @app.get(
        "/health",
        tags=["System"],
        summary="Health check",
        description="Returns service status, version, environment, and Redis connectivity.",
        response_description="Service health snapshot.",
    )
    async def health() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "version": _version,
                "env": os.getenv("ENV", "dev"),
                "redis": {"status": sm.status},
            }
        )

    @app.post(
        "/task",
        response_model=TaskResponse,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["Tasks"],
        summary="Submit a task",
        description=(
            "Accept a natural-language prompt and create a new task. "
            "The orchestrator builds an execution plan and starts running it in the background "
            "(unless `?run=false` is passed to defer execution). "
            "Returns `task_id` immediately — use it to poll status or connect via WebSocket."
        ),
        responses={
            202: {"description": "Task accepted and queued for execution."},
            422: {"description": "Validation error in request body."},
        },
    )
    async def submit_task(
        request: TaskRequest,
        background_tasks: BackgroundTasks,
        run: bool = True,
    ) -> TaskResponse:
        """
        Submit a task to the orchestrator.

        - **prompt**: natural-language instruction (e.g. *"Send carter01 to (10, 12)"*)
        - **task_id**: optional client-supplied identifier; auto-generated if omitted
        - **session_data**: opaque context forwarded to agents (last robot, locale, etc.)
        - **run**: set to `false` to create the task without starting it immediately
        """
        submit_result = await task_app_service.submit_task(
            prompt=request.prompt,
            session_data=request.session_data,
            run=run,
            background_tasks=background_tasks,
            external_task_id=request.task_id,
        )
        logger.info("Task %s accepted (run=%s)", submit_result.task_id, run)
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

        @app.get("/debug/crash/{task_id}", tags=["System"], include_in_schema=False)
        async def _crash(task_id: str):
            raise RuntimeError("Debug crash")

    return app


# Module-level app for uvicorn (`uvicorn orchestrator.app:app`)
app = create_app()
