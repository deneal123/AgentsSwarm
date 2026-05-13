"""Chat error handling utilities shared across application and worker layers."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException

from service.services.chat.domain.chat_exceptions import (
    ChatErrorMapper,
    JobCreationError,
    JobEnqueueError,
    JobExecutionError,
    JobOrchestrationError,
    JobServiceUnavailableError,
    ModelRoutingError,
)

_TRANSPORT_MAP = {
    ModelRoutingError: (422, "Model routing failed"),
    JobServiceUnavailableError: (503, "Job service unavailable"),
    JobCreationError: (500, "Failed to create chat job"),
    JobEnqueueError: (502, "Failed to enqueue chat task"),
    JobExecutionError: (504, "Failed to execute chat task"),
    JobOrchestrationError: (500, "Chat orchestration failed"),
}


def map_to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, HTTPException):
        return error
    for err_type, (status_code, message) in _TRANSPORT_MAP.items():
        if isinstance(error, err_type):
            return HTTPException(
                status_code=status_code,
                detail={"code": ChatErrorMapper.to_code(error), "message": message},
            )
    return HTTPException(
        status_code=500,
        detail={"code": ChatErrorMapper.to_code(error), "message": "Agent error"},
    )


def map_to_worker_error_payload(error: Exception, *, job_id: str) -> dict:
    http_exc = map_to_http_exception(error)
    detail = (
        http_exc.detail if isinstance(http_exc.detail, dict) else {"message": str(http_exc.detail)}
    )
    return {
        "type": "error",
        "job_id": job_id,
        "error": detail.get("message", "Agent error"),
        "error_code": detail.get("code", "chat_service_error"),
        "status_code": http_exc.status_code,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def normalize_response_metadata(
    metadata: dict | None, *, selected_model: str | None = None
) -> dict:
    data = dict(metadata or {})
    if selected_model and "selected_model" not in data:
        data["selected_model"] = selected_model
    return data
