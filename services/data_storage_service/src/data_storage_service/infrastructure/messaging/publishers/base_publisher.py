import logging
from typing import Any, Optional

from service.infrastructure.messaging.exceptions import PublisherError
from service.infrastructure.messaging.strategies import ExponentialBackoffRetry, RetryStrategy
from service.infrastructure.messaging.utils import safe_json_dumps, serialize_event

logger = logging.getLogger(__name__)


class BasePublisher:
    def __init__(self, retry_strategy: Optional[RetryStrategy] = None):
        self.retry_strategy = retry_strategy or ExponentialBackoffRetry(max_retries=3)

    async def publish_event(self, stream_key: str, event_type: str, data: dict[str, Any]) -> str:
        raise NotImplementedError

    async def publish_batch(self, stream_key: str, events: list[dict[str, Any]]) -> list[str]:
        raise NotImplementedError

    def publish_sync(self, stream_key: str, event_type: str, data: dict[str, Any]) -> str:
        raise NotImplementedError

    def _prepare_event_data(self, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        event_data = serialize_event(data)
        event_data["type"] = event_type
        return event_data

    def _record_success(self, stream_key: str, event_type: str):
        logger.info(f"Event published to {stream_key}: {event_type}")

    def _record_error(self, stream_key: str, error: Exception):
        error_type = type(error).__name__
        logger.error(f"Publish failed for {stream_key}: {error_type} - {error}")
