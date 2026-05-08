from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from orchestrator.services.orchestrator_runtime import OrchestratorRuntime
from orchestrator.services.tasks import TaskStore
from orchestrator.utils.logger import get_logger


logger = get_logger(__name__)


def _task_id_from_request(request: Request) -> str | None:
    return request.path_params.get("task_id") if hasattr(request, "path_params") else None


def register_exception_handlers(app: FastAPI, task_store: TaskStore, runtime: OrchestratorRuntime) -> None:

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Return 422 with structured field-level errors for Pydantic validation failures."""
        logger.warning(
            "Request validation error on %s: %s",
            request.url.path,
            exc.errors(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": exc.errors(),
                "body": exc.body,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Propagate HTTP exceptions; surface user-facing errors into the task stream."""
        task_id = _task_id_from_request(request)
        if task_id and task_store.get_task(task_id):
            runtime.record_user_error(
                task_id,
                message="Произошла ошибка при обработке запроса. Попробуйте ещё раз.",
                code=str(exc.status_code),
                detail=str(exc.detail),
            )
        if exc.status_code >= 500:
            logger.error(
                "HTTP %s on %s: %s",
                exc.status_code,
                request.url.path,
                exc.detail,
                extra={"task_id": task_id},
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch-all for unexpected errors; always returns 500."""
        task_id = _task_id_from_request(request)
        if task_id and task_store.get_task(task_id):
            runtime.record_user_error(
                task_id,
                message="Внутренняя ошибка. Мы уже разбираемся. Попробуйте повторить запрос чуть позже.",
                code="internal_error",
                detail=str(exc),
            )
        logger.exception(
            "Unhandled error on %s",
            request.url.path,
            extra={"task_id": task_id},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )


__all__ = ["register_exception_handlers"]
