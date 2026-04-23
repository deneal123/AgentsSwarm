from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from orchestrator.services.orchestrator_runtime import OrchestratorRuntime
from orchestrator.services.tasks import TaskStore
from orchestrator.utils.logger import get_logger


logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI, task_store: TaskStore, runtime: OrchestratorRuntime) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        task_ctx = request.path_params.get("task_id") if hasattr(request, "path_params") else None
        if task_ctx and task_store.get_task(task_ctx):
            runtime.record_user_error(
                task_ctx,
                message="Произошла ошибка при обработке запроса. Попробуйте ещё раз.",
                code=str(exc.status_code),
                detail=exc.detail,
            )
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        task_ctx = request.path_params.get("task_id") if hasattr(request, "path_params") else None
        if task_ctx and task_store.get_task(task_ctx):
            runtime.record_user_error(
                task_ctx,
                message="Внутренняя ошибка. Мы уже разбираемся. Попробуйте повторить запрос чуть позже.",
                code="internal_error",
                detail=str(exc),
            )
        logger.exception(
            "Unhandled error",
            extra={"path": request.url.path, "task_id": task_ctx},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )


__all__ = ["register_exception_handlers"]
