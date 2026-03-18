from __future__ import annotations

import logging
from typing import Optional

from redis.asyncio import Redis

from service.settings import RedisConfig

logger = logging.getLogger(__name__)


class RedisManager:
    """Lazily creates and manages a Redis asyncio client."""

    def __init__(self, config: RedisConfig) -> None:
        self._config = config
        self._client: Optional[Redis] = None

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def get_client(self) -> Redis:
        if not self.enabled:
            raise RuntimeError("Redis is disabled via configuration")

        if self._client is None:
            logger.info(
                "Initializing Redis client (host=%s, port=%s, db=%s)",
                self._config.host,
                self._config.port,
                self._config.db,
            )
            self._client = Redis(
                host=self._config.host,
                port=self._config.port,
                db=self._config.db,
                password=self._config.password or None,
                ssl=self._config.use_ssl,
                decode_responses=self._config.decode_responses,
                health_check_interval=self._config.health_check_interval,
            )
        return self._client

    async def ping(self) -> bool:
        if not self.enabled:
            return False
        client = self.get_client()
        try:
            return bool(await client.ping())
        except Exception:  # noqa: BLE001
            logger.exception("Redis ping failed")
            return False

    async def close(self) -> None:
        if self._client is None:
            return
        try:
            await self._client.close()
            await self._client.connection_pool.disconnect()
            logger.info("Redis client closed")
        except Exception:  # noqa: BLE001
            logger.exception("Error while closing Redis client")
        finally:
            self._client = None
