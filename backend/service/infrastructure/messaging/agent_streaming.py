import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from service.infrastructure.messaging import stream_helpers

logger = logging.getLogger(__name__)


class EventSerializer:
    @staticmethod
    def to_jsonable(value: Any) -> Any:
        try:
            return json.loads(json.dumps(value, default=str))
        except Exception:
            return str(value)

    def serialize(self, *, event: Any, job_id: str) -> dict[str, Any]:
        evt_type = event.type.value if hasattr(event.type, "value") else str(event.type)
        payload = {
            "type": evt_type,
            "job_id": job_id,
            "data": self.to_jsonable(event.data),
            "message": self.to_jsonable(event.data),
            "agent_name": event.agent_name,
            "metadata": self.to_jsonable(event.metadata or {}),
            "seq": getattr(event, "seq", 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if isinstance(event.metadata, dict) and event.metadata.get("tool_name"):
            payload["tool_name"] = event.metadata.get("tool_name")
        elif evt_type.startswith("tool_call") and isinstance(event.data, str):
            payload["tool_name"] = event.data
        return payload


class ReplyAssembler:
    def __init__(self) -> None:
        self.reply_parts: list[str] = []
        self.error_messages: list[str] = []
        self.metadata: dict[str, Any] = {}
        self.structured_output: Any = None

    def consume(self, *, event: Any, stream_chunk_type: Any, error_type: Any, structured_output_type: Any) -> None:
        if event.metadata:
            self.metadata.update(event.metadata)
        if event.type == stream_chunk_type and event.data is not None:
            self.reply_parts.append(str(event.data))
        elif event.type == error_type and event.data:
            self.error_messages.append(str(event.data))
        elif event.type == structured_output_type and event.data is not None:
            self.structured_output = event.data
            self.metadata = {**self.metadata, "structured_output": event.data}

    def build_reply(self) -> str:
        reply = "".join(self.reply_parts)
        if reply.strip():
            return reply
        if self.structured_output is None:
            return ""
        if isinstance(self.structured_output, str):
            return self.structured_output
        return json.dumps(self.structured_output, ensure_ascii=False)


class AgentStreamPublisher:
    def __init__(self, redis_client: Any, stream_key: str, retry_attempts: int = 3, retry_delay: float = 0.2) -> None:
        self.redis_client = redis_client
        self.stream_key = stream_key
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.closed = False

    def publish(self, payload: dict[str, Any]) -> bool:
        if self.closed or not self.redis_client:
            return False
        last_error: Exception | None = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                stream_helpers.xadd_sync(self.redis_client, self.stream_key, {"data": json.dumps(payload)})
                return True
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Failed to publish event to %s (attempt %s/%s)",
                    self.stream_key,
                    attempt,
                    self.retry_attempts,
                )
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_delay)
        if last_error:
            logger.exception("Failed to publish event to stream %s", self.stream_key, exc_info=last_error)
        return False

    def close(self) -> None:
        self.closed = True
