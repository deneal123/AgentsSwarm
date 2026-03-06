"""
Unit-тесты: RateLimiter (services/rate_limiter.py).

Покрывает:
  - Разрешённые запросы (токены есть)
  - Превышение лимита (токены исчерпаны)
  - Fail-open при redis=None
  - check_rest / check_chat методы → HTTP 429
  - bucket_key генерация (разные user_id → разные ключи)
  - reset() сбрасывает счётчик

Для тестов используется fakeredis.aioredis (или MagicMock).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from gateway_service.config import Settings
from gateway_service.services.rate_limiter import RateLimiter, get_rate_limiter


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_limiter(settings: Settings) -> RateLimiter:
    return RateLimiter(settings=settings)


def _make_request(app_redis: object = None) -> MagicMock:
    """Заглушка fastapi.Request."""
    request = MagicMock()
    request.app.state.redis = app_redis
    return request


# ─── Fail-open (redis=None) ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fail_open_when_redis_none(test_settings: Settings) -> None:
    """Без Redis все запросы разрешаются."""
    limiter = _make_limiter(test_settings)
    allowed = await limiter._is_allowed(
        redis_client=None,
        user_id="user-1",
        bucket="rest",
        capacity=100,
    )
    assert allowed is True


@pytest.mark.asyncio
async def test_fail_open_on_redis_exception(test_settings: Settings) -> None:
    """При ошибке Redis — fail-open."""
    redis = MagicMock()
    redis.client = MagicMock()
    redis.client.script_load = AsyncMock(side_effect=ConnectionError("Redis down"))

    limiter = _make_limiter(test_settings)
    allowed = await limiter._is_allowed(
        redis_client=redis,
        user_id="user-1",
        bucket="rest",
        capacity=100,
    )
    assert allowed is True


# ─── Token bucket logic (via mock evalsha) ───────────────────────────────────


@pytest.mark.asyncio
async def test_allowed_when_tokens_available(test_settings: Settings) -> None:
    """evalsha возвращает 1 → запрос разрешён."""
    redis = MagicMock()
    redis.client = MagicMock()
    redis.client.script_load = AsyncMock(return_value="sha123")
    redis.client.evalsha = AsyncMock(return_value=1)

    limiter = _make_limiter(test_settings)
    allowed = await limiter._is_allowed(
        redis_client=redis,
        user_id="user-1",
        bucket="rest",
        capacity=100,
    )
    assert allowed is True
    redis.client.evalsha.assert_called_once()


@pytest.mark.asyncio
async def test_blocked_when_no_tokens(test_settings: Settings) -> None:
    """evalsha возвращает 0 → запрос заблокирован."""
    redis = MagicMock()
    redis.client = MagicMock()
    redis.client.script_load = AsyncMock(return_value="sha123")
    redis.client.evalsha = AsyncMock(return_value=0)

    limiter = _make_limiter(test_settings)
    allowed = await limiter._is_allowed(
        redis_client=redis,
        user_id="user-1",
        bucket="rest",
        capacity=100,
    )
    assert allowed is False


# ─── check_rest / check_chat → HTTP 429 ──────────────────────────────────────


@pytest.mark.asyncio
async def test_check_rest_raises_429_when_blocked(test_settings: Settings) -> None:
    redis = MagicMock()
    redis.client = MagicMock()
    redis.client.script_load = AsyncMock(return_value="sha")
    redis.client.evalsha = AsyncMock(return_value=0)  # заблокирован

    limiter = _make_limiter(test_settings)
    request = _make_request(app_redis=redis)

    with pytest.raises(HTTPException) as exc_info:
        await limiter.check_rest("user-1", request)

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers is not None
    assert "Retry-After" in exc_info.value.headers


@pytest.mark.asyncio
async def test_check_chat_raises_429_when_blocked(test_settings: Settings) -> None:
    redis = MagicMock()
    redis.client = MagicMock()
    redis.client.script_load = AsyncMock(return_value="sha")
    redis.client.evalsha = AsyncMock(return_value=0)

    limiter = _make_limiter(test_settings)
    request = _make_request(app_redis=redis)

    with pytest.raises(HTTPException) as exc_info:
        await limiter.check_chat("user-1", request)

    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_check_rest_passes_when_allowed(test_settings: Settings) -> None:
    redis = MagicMock()
    redis.client = MagicMock()
    redis.client.script_load = AsyncMock(return_value="sha")
    redis.client.evalsha = AsyncMock(return_value=1)  # разрешён

    limiter = _make_limiter(test_settings)
    request = _make_request(app_redis=redis)

    # Не должен выбросить исключение
    await limiter.check_rest("user-1", request)


# ─── Different limits ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rest_uses_rate_limit_rest_per_minute(test_settings: Settings) -> None:
    """check_rest использует capacity=rate_limit_rest_per_minute."""
    redis = MagicMock()
    redis.client = MagicMock()
    redis.client.script_load = AsyncMock(return_value="sha")
    redis.client.evalsha = AsyncMock(return_value=1)

    limiter = _make_limiter(test_settings)
    request = _make_request(app_redis=redis)
    await limiter.check_rest("user-1", request)

    # Проверяем, что capacity передана правильно
    call_args = redis.client.evalsha.call_args
    # evalsha(sha, numkeys, key, capacity, rate, requested, now)
    # ARGV[1] = capacity → позиция [4] в вызове
    capacity_arg = call_args.args[3]  # 4-й positional arg
    assert capacity_arg == test_settings.rate_limit_rest_per_minute


@pytest.mark.asyncio
async def test_chat_uses_rate_limit_chat_per_minute(test_settings: Settings) -> None:
    """check_chat использует capacity=rate_limit_chat_per_minute."""
    redis = MagicMock()
    redis.client = MagicMock()
    redis.client.script_load = AsyncMock(return_value="sha")
    redis.client.evalsha = AsyncMock(return_value=1)

    limiter = _make_limiter(test_settings)
    request = _make_request(app_redis=redis)
    await limiter.check_chat("user-1", request)

    call_args = redis.client.evalsha.call_args
    capacity_arg = call_args.args[3]
    assert capacity_arg == test_settings.rate_limit_chat_per_minute


# ─── Bucket key isolation ─────────────────────────────────────────────────────


def test_different_users_get_different_keys(test_settings: Settings) -> None:
    limiter = _make_limiter(test_settings)
    key1 = limiter._bucket_key("user-aaa", "rest")
    key2 = limiter._bucket_key("user-bbb", "rest")
    assert key1 != key2


def test_same_user_different_buckets_get_different_keys(test_settings: Settings) -> None:
    limiter = _make_limiter(test_settings)
    key_rest = limiter._bucket_key("user-1", "rest")
    key_chat = limiter._bucket_key("user-1", "chat")
    assert key_rest != key_chat


def test_key_has_prefix(test_settings: Settings) -> None:
    limiter = _make_limiter(test_settings)
    key = limiter._bucket_key("user-1", "rest")
    assert key.startswith("rate_limit:")


# ─── get_remaining ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_remaining_returns_capacity_when_no_key(test_settings: Settings) -> None:
    redis = MagicMock()
    redis.client = MagicMock()
    redis.client.hmget = AsyncMock(return_value=[None])

    limiter = _make_limiter(test_settings)
    remaining = await limiter.get_remaining(redis, "user-1", "rest", capacity=100)
    assert remaining == 100


@pytest.mark.asyncio
async def test_get_remaining_returns_zero_when_exhausted(test_settings: Settings) -> None:
    redis = MagicMock()
    redis.client = MagicMock()
    redis.client.hmget = AsyncMock(return_value=["0"])

    limiter = _make_limiter(test_settings)
    remaining = await limiter.get_remaining(redis, "user-1", "rest", capacity=100)
    assert remaining == 0


@pytest.mark.asyncio
async def test_get_remaining_returns_capacity_when_redis_none(test_settings: Settings) -> None:
    limiter = _make_limiter(test_settings)
    remaining = await limiter.get_remaining(None, "user-1", "rest", capacity=50)
    assert remaining == 50


# ─── reset ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reset_calls_delete(test_settings: Settings) -> None:
    redis = MagicMock()
    redis.client = MagicMock()
    redis.client.delete = AsyncMock(return_value=1)

    limiter = _make_limiter(test_settings)
    await limiter.reset(redis, "user-1", "rest")
    redis.client.delete.assert_called_once()


@pytest.mark.asyncio
async def test_reset_noop_when_redis_none(test_settings: Settings) -> None:
    limiter = _make_limiter(test_settings)
    # Не должен выбросить исключение
    await limiter.reset(None, "user-1", "rest")


# ─── Singleton ────────────────────────────────────────────────────────────────


def test_get_rate_limiter_returns_singleton(test_settings) -> None:
    from unittest.mock import patch
    from gateway_service.services import rate_limiter as rl_module
    rl_module._rate_limiter = None  # сбрасываем singleton

    with patch("gateway_service.services.rate_limiter.get_settings", return_value=test_settings):
        lim1 = get_rate_limiter()
        lim2 = get_rate_limiter()
    assert lim1 is lim2
