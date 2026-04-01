"""Session manager with optional Redis backend.

Defaults to an in-memory dictionary. Redis can be enabled via `REDIS_URL`.
Provides a lightweight status probe for health endpoints.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

try:
    from redis.asyncio import Redis  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Redis = None  # type: ignore


class SessionManager:
    def __init__(self) -> None:
        self._redis_url = os.getenv("REDIS_URL")
        self._redis: Optional[Redis] = None
        self._memory: dict[str, Dict[str, Any]] = {}
        # Default to disabled until connect() runs; avoids "pending" in health before lifespan
        self._status: str = "disabled"

    async def connect(self) -> None:
        if self._redis_url and Redis is not None:
            try:
                self._redis = Redis.from_url(self._redis_url, decode_responses=True)
                await self._redis.ping()
                self._status = "ok"
            except Exception:
                self._redis = None
                self._status = "error"
        else:
            self._status = "disabled"

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()

    async def get_session(self, task_id: str) -> Dict[str, Any]:
        if self._redis:
            data = await self._redis.hgetall(task_id)
            return self._decode_session(data)
        return self._memory.get(task_id, {})

    async def update_session(self, task_id: str, context: Dict[str, Any]) -> None:
        if self._redis:
            if context:
                await self._redis.hset(task_id, mapping=self._encode_session(context))
            return
        self._memory[task_id] = context

    async def clear_session(self, task_id: str) -> None:
        if self._redis:
            await self._redis.delete(task_id)
            return
        self._memory.pop(task_id, None)

    async def append_history(self, task_id: str, message: str) -> None:
        session = await self.get_session(task_id)
        history: List[str] = session.get("history", [])
        history.append(message)
        session["history"] = history
        await self.update_session(task_id, session)

    async def set_last_robot(self, task_id: str, robot_id: str) -> None:
        session = await self.get_session(task_id)
        session["last_robot_id"] = robot_id
        await self.update_session(task_id, session)

    async def cache_mcp_result(self, task_id: str, key: str, value: Any) -> None:
        session = await self.get_session(task_id)
        cache = session.get("mcp_cache", {})
        cache[key] = value
        session["mcp_cache"] = cache
        await self.update_session(task_id, session)

    def _encode_session(self, ctx: Dict[str, Any]) -> Dict[str, str]:
        encoded: Dict[str, str] = {}
        for k, v in ctx.items():
            if isinstance(v, (dict, list)):
                encoded[k] = json.dumps(v)
            else:
                encoded[k] = str(v)
        return encoded

    def _decode_session(self, data: Dict[str, str]) -> Dict[str, Any]:
        decoded: Dict[str, Any] = {}
        for k, v in data.items():
            if not v:
                decoded[k] = v
                continue
            if v.startswith("[") or v.startswith("{"):
                try:
                    decoded[k] = json.loads(v)
                    continue
                except Exception:
                    pass
            decoded[k] = v
        return decoded

    @property
    def status(self) -> str:
        return self._status


# Dependency provider for FastAPI DI

def get_session_manager() -> SessionManager:
    return SessionManager()
