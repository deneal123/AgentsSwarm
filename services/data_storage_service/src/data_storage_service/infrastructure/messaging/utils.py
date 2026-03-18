import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def create_event_loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop


def run_async_in_sync(coro: Callable[..., Any], *args, **kwargs) -> Any:
    loop = create_event_loop()
    try:
        return loop.run_until_complete(coro(*args, **kwargs))
    finally:
        try:
            loop.close()
        except Exception as e:
            logger.debug(f"Error closing event loop: {e}")


def serialize_event(data: dict[str, Any]) -> dict[str, Any]:
    serialized = {}
    for key, value in data.items():
        if isinstance(value, Enum):
            serialized[key] = value.value
        elif isinstance(value, datetime):
            serialized[key] = value.isoformat()
        elif isinstance(value, (uuid.UUID,)):
            serialized[key] = str(value)
        else:
            serialized[key] = value
    return serialized


def generate_trace_id() -> str:
    return str(uuid.uuid4())


def safe_json_dumps(obj: Any) -> str:
    try:
        if isinstance(obj, str):
            return obj
        return json.dumps(serialize_event(obj) if isinstance(obj, dict) else obj)
    except Exception as e:
        logger.error(f"JSON serialization failed: {e}")
        return json.dumps({"error": "serialization_failed", "original_type": str(type(obj))})


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)
