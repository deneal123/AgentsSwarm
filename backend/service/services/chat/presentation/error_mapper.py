"""Re-exports from application error_handling for presentation-layer consumers."""
from service.services.chat.application.error_handling import (
    map_to_http_exception,
    map_to_worker_error_payload,
    normalize_response_metadata,
)

from fastapi import HTTPException


def map_to_ws_error_payload(error: Exception, *, message_id: str | None = None) -> dict:
    from datetime import datetime, timezone

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


__all__ = [
    "map_to_http_exception",
    "map_to_worker_error_payload",
    "map_to_ws_error_payload",
    "normalize_response_metadata",
]
