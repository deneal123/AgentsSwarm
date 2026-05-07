from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ChatWorkerDependencyFactory:
    def create_pg_connector(self, config: Any):
        from service.infrastructure.database.postgresql import PgConnector

        return PgConnector(config.pg)

    def create_redis_client(self, config: Any):
        if not config.redis or not config.redis.enabled:
            return None
        import redis as redis_sync

        return redis_sync.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password or None,
            decode_responses=True,
        )
