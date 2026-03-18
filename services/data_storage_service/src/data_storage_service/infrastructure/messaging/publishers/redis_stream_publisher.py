import logging
from typing import Any, Optional

from service.infrastructure.messaging.exceptions import StreamPublishError
from service.infrastructure.messaging.publishers.base_publisher import BasePublisher
from service.infrastructure.messaging.strategies import RetryStrategy
from service.infrastructure.messaging.utils import safe_json_dumps

logger = logging.getLogger(__name__)


class RedisStreamPublisher(BasePublisher):
    def __init__(self, redis_client: Any, retry_strategy: Optional[RetryStrategy] = None):
        super().__init__(retry_strategy)
        self.redis_client = redis_client

    async def publish_event(self, stream_key: str, event_type: str, data: dict[str, Any]) -> str:
        event_data = self._prepare_event_data(event_type, data)
        payload = {"data": safe_json_dumps(event_data)}

        attempt = 0
        last_error = None

        while attempt <= self.retry_strategy.max_retries:
            try:
                result = await self.redis_client.xadd(stream_key, payload)
                self._record_success(stream_key, event_type)
                logger.info(f"Published event to {stream_key}: {event_type}")
                return result
            except Exception as e:
                last_error = e
                self._record_error(stream_key, e)

                if not self.retry_strategy.should_retry(e, attempt):
                    break

                delay = self.retry_strategy.get_delay(attempt)
                logger.warning(
                    f"Publish failed (attempt {attempt + 1}/{self.retry_strategy.max_retries}), "
                    f"retrying in {delay}s"
                )
                import asyncio

                await asyncio.sleep(delay)
                attempt += 1

        raise StreamPublishError(f"Failed to publish after {attempt} attempts: {last_error}")

    async def publish_batch(self, stream_key: str, events: list[dict[str, Any]]) -> list[str]:
        results = []
        for event in events:
            event_type = event.get("type", "unknown")
            result = await self.publish_event(stream_key, event_type, event)
            results.append(result)
        return results

    def publish_sync(self, stream_key: str, event_type: str, data: dict[str, Any]) -> str:
        event_data = self._prepare_event_data(event_type, data)
        payload = {"data": safe_json_dumps(event_data)}

        attempt = 0
        last_error = None

        while attempt <= self.retry_strategy.max_retries:
            try:
                result = self.redis_client.xadd(stream_key, payload)
                self._record_success(stream_key, event_type)
                logger.info(f"Published event to {stream_key}: {event_type}")
                return result
            except Exception as e:
                last_error = e
                self._record_error(stream_key, e)

                if not self.retry_strategy.should_retry(e, attempt):
                    break

                delay = self.retry_strategy.get_delay(attempt)
                logger.warning(
                    f"Publish failed (attempt {attempt + 1}/{self.retry_strategy.max_retries}), "
                    f"retrying in {delay}s"
                )
                import time

                time.sleep(delay)
                attempt += 1

        raise StreamPublishError(f"Failed to publish after {attempt} attempts: {last_error}")
