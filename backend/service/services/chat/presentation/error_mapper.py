from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from service.services.chat.domain.chat_exceptions import map_chat_exception_to_http


def map_to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, HTTPException):
        return error
    return map_chat_exception_to_http(error)


def map_to_ws_error_payload(error: Exception, *, message_id: str | None = None) -> dict:
    http_exc = map_to_http_exception(error)
    detail = http_exc.detail if isinstance(http_exc.detail, dict) else {"message": str(http_exc.detail)}
    return {
        "type": "error",
        "message_id": message_id,
        "error": detail.get("message", "Agent error"),
        "error_code": detail.get("code", "chat_service_error"),
        "status_code": http_exc.status_code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def map_to_worker_error_payload(error: Exception, *, job_id: str) -> dict:
    http_exc = map_to_http_exception(error)
    detail = http_exc.detail if isinstance(http_exc.detail, dict) else {"message": str(http_exc.detail)}
    return {
        "type": "error",
        "job_id": job_id,
        "error": detail.get("message", "Agent error"),
        "error_code": detail.get("code", "chat_service_error"),
        "status_code": http_exc.status_code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def normalize_response_metadata(metadata: dict | None, *, selected_model: str | None = None) -> dict:
    data = dict(metadata or {})
    if selected_model and "selected_model" not in data:
        data["selected_model"] = selected_model
    return data
