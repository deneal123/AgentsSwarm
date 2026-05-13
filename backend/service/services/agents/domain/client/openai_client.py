"""Native OpenAI client (non-MWS) with MWS-compatible helper API.

Этот модуль предоставляет клиента OpenAI и обёртки с теми же сигнатурами,
что и у MWS-клиента (`mws_client`), чтобы их можно было взаимозаменяемо
подключать в коде и для OpenAI Agents SDK.
"""

import asyncio
import logging
import time
from typing import Any

import httpx
from openai import AsyncOpenAI

from agents import set_default_openai_client, set_default_openai_key, set_tracing_disabled
from service.settings import config

logger = logging.getLogger(__name__)

DEFAULT_MODELS_CACHE_TTL_SEC = 180

_MODELS_CACHE: dict[str, object] = {"items": [], "expires_at": 0.0}
_MODELS_LOCK = asyncio.Lock()


def _make_http_client() -> httpx.AsyncClient:
    """Build Async HTTP client with optional proxy for OpenAI."""
    if config.agents.proxy_host and config.agents.proxy_port:
        try:
            proxy_url = (
                f"http://{config.agents.proxy_user or ''}:{config.agents.proxy_pass or ''}"
                f"@{config.agents.proxy_host}:{config.agents.proxy_port}"
            )
            return httpx.AsyncClient(proxies=proxy_url)
        except Exception:
            logger.exception("Failed to build proxy client; falling back to default HTTP client")
    return httpx.AsyncClient()


OPENAI_API_KEY = config.agents.openai_api_key
BASE_URL = config.agents.openai_base_url


def create_openai_client() -> AsyncOpenAI | None:
    """Create AsyncOpenAI client for the native OpenAI endpoint.

    По умолчанию также настраивает OpenAI Agents SDK на использование этого
    клиента, если ключ задан.
    """
    api_key = (OPENAI_API_KEY or "").strip()
    base_url = (BASE_URL or "").strip() or None
    if not api_key:
        logger.warning("OpenAI client is not configured: missing AGENTS__OPENAI_API_KEY")
        return None

    try:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=_make_http_client(),
        )
        set_default_openai_key(api_key)
        set_default_openai_client(client)
        set_tracing_disabled(disabled=True)
        return client
    except Exception:
        logger.exception("Failed to initialize OpenAI client")
        return None


try:
    OPENAI_CLIENT = create_openai_client()
except Exception:
    OPENAI_CLIENT = None


def _models_cache_ttl() -> int:
    ttl = DEFAULT_MODELS_CACHE_TTL_SEC
    return max(1, int(ttl))


def _normalize_model_list(raw_items: Any) -> list[str]:
    model_ids: set[str] = set()
    for item in raw_items or []:
        mid = None
        if isinstance(item, dict):
            mid = item.get("id")
        else:
            mid = getattr(item, "id", None)
        if isinstance(mid, str) and mid.strip():
            model_ids.add(mid.strip())
    return sorted(model_ids)


async def list_available_models(
    client: AsyncOpenAI | None = None,
    force_refresh: bool = False,
) -> list[str]:
    """List models from the OpenAI API (cached, MWS-compatible signature)."""
    target_client = client or OPENAI_CLIENT
    if target_client is None:
        return []

    now = time.monotonic()
    cached_items = _MODELS_CACHE.get("items", [])
    expires_at = float(_MODELS_CACHE.get("expires_at", 0.0) or 0.0)
    if not force_refresh and now < expires_at and isinstance(cached_items, list):
        return list(cached_items)

    async with _MODELS_LOCK:
        now = time.monotonic()
        cached_items = _MODELS_CACHE.get("items", [])
        expires_at = float(_MODELS_CACHE.get("expires_at", 0.0) or 0.0)
        if not force_refresh and now < expires_at and isinstance(cached_items, list):
            return list(cached_items)

        try:
            response = await target_client.models.list()
            models = _normalize_model_list(getattr(response, "data", []))
            _MODELS_CACHE["items"] = models
            _MODELS_CACHE["expires_at"] = time.monotonic() + _models_cache_ttl()
            return list(models)
        except Exception:
            logger.exception("Failed to fetch available models from OpenAI API")
            if isinstance(cached_items, list):
                return list(cached_items)
            return []


async def create_chat_completion(
    messages: list[dict[str, str]],
    model: str,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    n: int | None = None,
    presence_penalty: float | None = None,
    frequency_penalty: float | None = None,
    client: AsyncOpenAI | None = None,
):
    """Call OpenAI chat completions endpoint (/v1/chat/completions)."""
    target_client = client or OPENAI_CLIENT
    if target_client is None:
        raise RuntimeError("OpenAI client is not configured")

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if n is not None:
        payload["n"] = n
    if presence_penalty is not None:
        payload["presence_penalty"] = presence_penalty
    if frequency_penalty is not None:
        payload["frequency_penalty"] = frequency_penalty

    return await target_client.chat.completions.create(**payload)


async def create_completion(
    prompt: str,
    model: str,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    top_p: float | None = None,
    frequency_penalty: float | None = None,
    presence_penalty: float | None = None,
    stop: list[str] | None = None,
    client: AsyncOpenAI | None = None,
):
    """Call OpenAI completions endpoint (/v1/completions)."""
    target_client = client or OPENAI_CLIENT
    if target_client is None:
        raise RuntimeError("OpenAI client is not configured")

    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if top_p is not None:
        payload["top_p"] = top_p
    if frequency_penalty is not None:
        payload["frequency_penalty"] = frequency_penalty
    if presence_penalty is not None:
        payload["presence_penalty"] = presence_penalty
    if stop is not None:
        payload["stop"] = stop

    return await target_client.completions.create(**payload)


async def create_embedding(
    text: str,
    model: str,
    *,
    client: AsyncOpenAI | None = None,
):
    """Call OpenAI embeddings endpoint (/v1/embeddings)."""
    target_client = client or OPENAI_CLIENT
    if target_client is None:
        raise RuntimeError("OpenAI client is not configured")
    return await target_client.embeddings.create(model=model, input=text)


def clear_models_cache() -> None:
    _MODELS_CACHE["items"] = []
    _MODELS_CACHE["expires_at"] = 0.0
