import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class BaseConsumer:
    def __init__(
        self,
        redis_client: Any,
        stream_key: str,
        consumer_group: str = "default",
        consumer_name: str = "worker",
    ):
        self.redis_client = redis_client
        self.stream_key = stream_key
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        self._running = False

    async def consume_message(self, message_id: str, data: dict[str, Any]) -> bool:
        raise NotImplementedError

    async def start(self, block_ms: int = 5000):
        self._running = True

        try:
            await self.redis_client.xgroup_create(
                self.stream_key, self.consumer_group, id="0", mkstream=True
            )
        except Exception:
            pass

        logger.info(f"Consumer started for {self.stream_key}")

        while self._running:
            try:
                messages = await self.redis_client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {self.stream_key: ">"},
                    count=10,
                    block=block_ms,
                )

                for stream, msg_list in messages:
                    for message_id, data in msg_list:
                        try:
                            success = await self.consume_message(message_id, data)
                            if success:
                                await self.redis_client.xack(
                                    self.stream_key, self.consumer_group, message_id
                                )
                        except Exception as e:
                            logger.exception(f"Error consuming message {message_id}: {e}")

            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                import asyncio

                await asyncio.sleep(1)

    async def stop(self):
        self._running = False
        logger.info(f"Consumer stopped for {self.stream_key}")

    async def reclaim_pending(self, idle_time_ms: int = 60000):
        try:
            pending = await self.redis_client.xpending_range(
                self.stream_key,
                self.consumer_group,
                min="-",
                max="+",
                count=100,
            )

            for msg in pending:
                if msg["time_since_delivered"] > idle_time_ms:
                    message_id = msg["message_id"]
                    await self.redis_client.xclaim(
                        self.stream_key,
                        self.consumer_group,
                        self.consumer_name,
                        min_idle_time=idle_time_ms,
                        message_ids=[message_id],
                    )
                    logger.info(f"Reclaimed pending message {message_id}")

        except Exception as e:
            logger.error(f"Error reclaiming pending messages: {e}")
