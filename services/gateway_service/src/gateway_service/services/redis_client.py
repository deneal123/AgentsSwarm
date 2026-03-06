"""Redis клиент: connection pool, pub/sub, кэш, streams."""

from __future__ import annotations

import structlog
from redis.asyncio import ConnectionPool, Redis
from redis.asyncio.client import PubSub
from redis.exceptions import ConnectionError as RedisConnectionError

logger = structlog.get_logger(__name__)


class RedisClient:
    """Обёртка над redis.asyncio с connection pool и helper-методами."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None  # type: ignore[type-arg]

    async def connect(self) -> None:
        self._pool = ConnectionPool.from_url(
            self._url,
            decode_responses=True,
            max_connections=20,
            socket_keepalive=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )
        self._client = Redis(connection_pool=self._pool)
        # Проверяем соединение
        await self._client.ping()
        logger.info("redis.pool_created", url=self._url)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
        if self._pool:
            await self._pool.aclose()
        logger.info("redis.closed")

    @property
    def client(self) -> Redis:  # type: ignore[type-arg]
        if self._client is None:
            raise RuntimeError("RedisClient not connected. Call connect() first.")
        return self._client

    # ─── Базовые операции ────────────────────────────────────────────────────

    async def get(self, key: str) -> str | None:
        return await self.client.get(key)  # type: ignore[return-value]

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        if ttl:
            await self.client.setex(key, ttl, value)
        else:
            await self.client.set(key, value)

    async def delete(self, *keys: str) -> int:
        return await self.client.delete(*keys)  # type: ignore[return-value]

    async def exists(self, key: str) -> bool:
        return bool(await self.client.exists(key))

    async def hset(self, name: str, mapping: dict[str, str]) -> None:
        await self.client.hset(name, mapping=mapping)  # type: ignore[arg-type]

    async def hgetall(self, name: str) -> dict[str, str]:
        return await self.client.hgetall(name)  # type: ignore[return-value]

    # ─── Pub/Sub ──────────────────────────────────────────────────────────────

    async def publish(self, channel: str, message: str) -> int:
        return await self.client.publish(channel, message)  # type: ignore[return-value]

    def pubsub(self) -> PubSub:
        return self.client.pubsub()

    # ─── Health check ────────────────────────────────────────────────────────

    async def ping(self) -> bool:
        try:
            return await self.client.ping()  # type: ignore[return-value]
        except (RedisConnectionError, Exception):
            return False
