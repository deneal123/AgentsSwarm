"""
Rate Limiter — алгоритм Token Bucket на Redis.

Lua-скрипт обеспечивает атомарность: проверка + декремент — одна операция.

Лимиты (по умолчанию из settings):
  REST API : 100 запросов / 60 секунд  (per user_id)
  Chat WS  : 30  сообщений / 60 секунд (per user_id)

Использование (FastAPI Depends):
    from gateway_service.services.rate_limiter import RateLimiter, get_rate_limiter

    # В роутере:
    @router.post("/message")
    async def send_message(
        limiter: RateLimiter = Depends(get_rate_limiter),
        current_user: UserContext = Depends(get_current_user),
    ):
        await limiter.check_chat(current_user.user_id, request)
        ...

    # Как middleware (для REST):
    await limiter.check_rest(user_id, request)
"""

from __future__ import annotations

import hashlib
import time

import structlog
from fastapi import HTTPException, Request, status

from gateway_service.config import Settings, get_settings

logger = structlog.get_logger(__name__)

# ─── Lua script: Token Bucket ─────────────────────────────────────────────────
# Ключ: rate_limit:{user_id}:{bucket_name}
# Поля hash:
#   tokens   — текущее кол-во токенов (float как строка)
#   last_ts  — unix timestamp последнего refill (float как строка)
#
# Аргументы: KEYS[1]=key, ARGV[1]=capacity, ARGV[2]=refill_rate (tokens/sec),
#             ARGV[3]=requested (обычно 1), ARGV[4]=now (unix timestamp float)
#
# Возвращает: 1 (allowed) или 0 (rate limited)

_TOKEN_BUCKET_LUA = """
local key       = KEYS[1]
local capacity  = tonumber(ARGV[1])
local rate      = tonumber(ARGV[2])
local requested = tonumber(ARGV[3])
local now       = tonumber(ARGV[4])

local data = redis.call("HMGET", key, "tokens", "last_ts")
local tokens  = tonumber(data[1]) or capacity
local last_ts = tonumber(data[2]) or now

-- refill
local elapsed = math.max(0, now - last_ts)
tokens = math.min(capacity, tokens + elapsed * rate)

if tokens >= requested then
    tokens = tokens - requested
    redis.call("HMSET", key, "tokens", tokens, "last_ts", now)
    redis.call("EXPIRE", key, math.ceil(capacity / rate) + 10)
    return 1
else
    redis.call("HMSET", key, "tokens", tokens, "last_ts", now)
    redis.call("EXPIRE", key, math.ceil(capacity / rate) + 10)
    return 0
end
"""

_SCRIPT_SHA: dict[str, str] = {}  # redis URL → EVALSHA digest


class RateLimiter:
    """
    Token Bucket rate limiter на Redis.

    Параметры бакетов задаются через Settings:
      rest : capacity=rate_limit_rest_per_minute,  window=60 сек
      chat : capacity=rate_limit_chat_per_minute,  window=60 сек

    Fail-open: при недоступном Redis запросы проходят.
    """

    _KEY_PREFIX = "rate_limit"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _bucket_key(self, user_id: str, bucket: str) -> str:
        # Хэшируем user_id чтобы не хранить UUID в ключе Redis напрямую
        uid_hash = hashlib.sha256(user_id.encode()).hexdigest()[:16]
        return f"{self._KEY_PREFIX}:{uid_hash}:{bucket}"

    async def _is_allowed(
        self,
        redis_client: object,
        user_id: str,
        bucket: str,
        capacity: int,
        window_seconds: int = 60,
    ) -> bool:
        """
        Проверить и уменьшить счётчик токенов.
        Возвращает True если запрос разрешён.
        """
        if redis_client is None:
            return True  # fail-open

        try:
            rc = redis_client.client  # type: ignore[attr-defined]
            key = self._bucket_key(user_id, bucket)
            rate = capacity / window_seconds  # tokens per second
            now = time.time()

            # Загружаем или используем кэшированный SHA
            redis_url = self._settings.redis_url
            if redis_url not in _SCRIPT_SHA:
                sha = await rc.script_load(_TOKEN_BUCKET_LUA)
                _SCRIPT_SHA[redis_url] = sha

            result = await rc.evalsha(
                _SCRIPT_SHA[redis_url],
                1,             # numkeys
                key,           # KEYS[1]
                capacity,      # ARGV[1]
                rate,          # ARGV[2]
                1,             # ARGV[3] — requested tokens
                now,           # ARGV[4]
            )
            return bool(result)

        except Exception as exc:
            logger.warning("rate_limiter.redis_error", error=str(exc), user_id=user_id[:8])
            return True  # fail-open при ошибке Redis

    async def _enforce(
        self,
        request: Request,
        user_id: str,
        bucket: str,
        capacity: int,
        window_seconds: int = 60,
    ) -> None:
        """Выбросить HTTP 429 если лимит превышен."""
        redis_client = getattr(request.app.state, "redis", None)
        allowed = await self._is_allowed(redis_client, user_id, bucket, capacity, window_seconds)
        if not allowed:
            logger.warning(
                "rate_limit.exceeded",
                user_id=user_id[:8],
                bucket=bucket,
                capacity=capacity,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Too many requests. Limit: {capacity} per {window_seconds}s.",
                },
                headers={"Retry-After": str(window_seconds)},
            )

    # ─── Public API ───────────────────────────────────────────────────────────

    async def check_rest(self, user_id: str, request: Request) -> None:
        """Проверить лимит REST API (100 req/min по умолчанию)."""
        await self._enforce(
            request,
            user_id,
            bucket="rest",
            capacity=self._settings.rate_limit_rest_per_minute,
        )

    async def check_chat(self, user_id: str, request: Request) -> None:
        """Проверить лимит чат-сообщений (30 msg/min по умолчанию)."""
        await self._enforce(
            request,
            user_id,
            bucket="chat",
            capacity=self._settings.rate_limit_chat_per_minute,
        )

    async def get_remaining(
        self,
        redis_client: object,
        user_id: str,
        bucket: str,
        capacity: int,
    ) -> int:
        """
        Вернуть оставшееся кол-во токенов (без декремента).
        Используется для заголовков X-RateLimit-Remaining.
        """
        if redis_client is None:
            return capacity
        try:
            rc = redis_client.client  # type: ignore[attr-defined]
            key = self._bucket_key(user_id, bucket)
            data = await rc.hmget(key, "tokens")
            tokens = data[0]
            return max(0, int(float(tokens))) if tokens else capacity
        except Exception:
            return capacity

    async def reset(self, redis_client: object, user_id: str, bucket: str) -> None:
        """Сбросить счётчик (для тестов или ручного сброса администратором)."""
        if redis_client is None:
            return
        try:
            rc = redis_client.client  # type: ignore[attr-defined]
            await rc.delete(self._bucket_key(user_id, bucket))
        except Exception as exc:
            logger.warning("rate_limiter.reset_failed", error=str(exc))


# ─── Singleton & Depends ──────────────────────────────────────────────────────

_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """FastAPI Depends-совместимый синглтон RateLimiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(get_settings())
    return _rate_limiter
