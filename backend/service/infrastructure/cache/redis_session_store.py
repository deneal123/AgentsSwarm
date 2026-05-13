from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from redis.asyncio import Redis

from service.models.db.db_models import UserSession
from service.settings import RedisConfig

logger = logging.getLogger(__name__)


class RedisSessionStore:
    """Stores user sessions in Redis for quick lookup and revocation."""

    def __init__(self, client: Redis, config: RedisConfig) -> None:
        self._client = client
        self._config = config
        self._session_prefix = f"{config.session_prefix}:id"
        self._user_index_prefix = f"{config.session_prefix}:user"
        self._token_index_prefix = f"{config.session_prefix}:token"

    def _session_key(self, session_id: UUID | str) -> str:
        return f"{self._session_prefix}:{session_id}"

    def _user_sessions_key(self, user_id: UUID | str) -> str:
        return f"{self._user_index_prefix}:{user_id}"

    def _token_key(self, token: str) -> str:
        return f"{self._token_index_prefix}:{token}"

    async def store_session(self, session: UserSession) -> None:
        ttl_seconds = max(
            int((session.expires_at - datetime.now(UTC)).total_seconds()),
            1,
        )
        payload = {
            "id": str(session.id),
            "user_id": str(session.user_id),
            "fingerprint": session.fingerprint,
            "status": session.status,
            "token": session.token,
            "expires_at": session.expires_at.isoformat(),
            "user_agent": session.user_agent,
        }

        session_key = self._session_key(session.id)
        user_key = self._user_sessions_key(session.user_id)
        token_key = self._token_key(session.token or "")

        await cast(Any, self._client.set(session_key, json.dumps(payload), ex=ttl_seconds))
        await cast(Any, self._client.sadd(user_key, str(session.id)))
        await cast(
            Any, self._client.expire(user_key, max(ttl_seconds, self._config.session_ttl_seconds))
        )

        if session.token:
            await self._client.set(token_key, str(session.id), ex=ttl_seconds)

    async def get_session(self, session_id: UUID | str) -> dict[str, Any] | None:
        raw = await self._client.get(self._session_key(session_id))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:  # noqa: PERF203
            logger.warning("Invalid session JSON for %s; removing", session_id)
            await self.invalidate_session(session_id)
            return None

    async def get_session_by_token(self, token: str) -> dict[str, Any] | None:
        if not token:
            return None
        session_id = await self._client.get(self._token_key(token))
        if not session_id:
            return None
        return await self.get_session(session_id)

    async def invalidate_session(self, session_id: UUID | str) -> None:
        session_key = self._session_key(session_id)
        raw = await self._client.get(session_key)
        if raw:
            try:
                data = json.loads(raw)
                token = data.get("token")
                if token:
                    await self._client.delete(self._token_key(token))
            except json.JSONDecodeError:  # noqa: PERF203
                logger.debug("Unable to decode session payload during invalidation: %s", session_id)
        await self._client.delete(session_key)

    async def invalidate_user_sessions(self, user_id: UUID | str) -> None:
        user_key = self._user_sessions_key(user_id)
        session_ids = await cast(Any, self._client.smembers(user_key))
        if not session_ids:
            return

        for session_id in session_ids:
            await self.invalidate_session(session_id)
        await self._client.delete(user_key)
