from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio import Redis

from service.settings import RedisConfig

logger = logging.getLogger(__name__)


class RedisCacheService:
    """High-level helper for JSON caching in Redis."""

    def __init__(self, client: Redis, config: RedisConfig) -> None:
        self._client = client
        self._config = config

    def _key(self, namespace: str, identifier: str) -> str:
        return f"{self._config.cache_prefix}:{namespace}:{identifier}"

    async def get_json(self, namespace: str, identifier: str) -> dict[str, Any] | None:
        key = self._key(namespace, identifier)
        raw = await self._client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:  # noqa: PERF203
            logger.warning("Invalid JSON cached for key=%s; purging", key)
            await self._client.delete(key)
            return None

    async def set_json(
        self,
        namespace: str,
        identifier: str,
        payload: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> None:
        key = self._key(namespace, identifier)
        ttl = ttl_seconds or self._config.cache_default_ttl_seconds
        await self._client.set(key, json.dumps(payload, default=str), ex=max(ttl, 1))

    async def invalidate(self, namespace: str, identifier: str) -> None:
        key = self._key(namespace, identifier)
        await self._client.delete(key)

    async def invalidate_many(self, namespace: str, identifiers: list[str]) -> None:
        if not identifiers:
            return
        keys = [self._key(namespace, identifier) for identifier in identifiers]
        await self._client.delete(*keys)
