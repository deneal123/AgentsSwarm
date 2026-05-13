"""OpenRouter client with MWS/OpenAI-compatible helper API.

Этот модуль предоставляет клиента OpenRouter и обёртки с теми же сигнатурами,
что и у mws_client / openai_client, чтобы их можно было взаимозаменяемо
подключать в коде и для OpenAI Agents SDK.

OpenRouter совместим с OpenAI API (base_url = https://openrouter.ai/api/v1),
поэтому используем AsyncOpenAI как транспорт.
"""

import asyncio
import logging
import time
from typing import Any

import httpx
from openai import AsyncOpenAI

from service.settings import config

logger = logging.getLogger(__name__)

try:
    from agents import set_default_openai_client, set_default_openai_key, set_tracing_disabled
except Exception:  # pragma: no cover

    def set_default_openai_client(_client):
        return None

    def set_default_openai_key(_key):
        return None

    def set_tracing_disabled(*, disabled: bool):
        return None


DEFAULT_OPENROUTER_TIMEOUT_SEC = 20.0
DEFAULT_MODELS_CACHE_TTL_SEC = 180
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

_MODELS_CACHE: dict[str, object] = {"items": [], "expires_at": 0.0}
_MODELS_LOCK = asyncio.Lock()


def _resolve_openrouter_base_url() -> str:
    raw = (config.agents.openrouter_base_url or "").strip()
    if not raw:
        return DEFAULT_OPENROUTER_BASE_URL
    base = raw.rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return base


def _build_proxy_url() -> str:
    host = (config.agents.proxy_host or "").strip()
    if not host or not config.agents.proxy_port:
        return ""
    user = (config.agents.proxy_user or "").strip()
    password = (config.agents.proxy_pass or "").strip()
    if user or password:
        return f"http://{user}:{password}@{host}:{config.agents.proxy_port}"
    return f"http://{host}:{config.agents.proxy_port}"


def _make_http_client() -> httpx.AsyncClient:
    timeout = config.agents.openrouter_timeout_sec or DEFAULT_OPENROUTER_TIMEOUT_SEC
    proxy_url = _build_proxy_url()
    try:
        if proxy_url:
            return httpx.AsyncClient(proxies=proxy_url, timeout=timeout)
        return httpx.AsyncClient(timeout=timeout)
    except Exception:
        logger.exception("Failed to build HTTP client for OpenRouter")
        return httpx.AsyncClient(timeout=timeout)


OPENROUTER_API_KEY = config.agents.openrouter_api_key
OPENROUTER_BASE_URL = _resolve_openrouter_base_url()

# Backward-compatible aliases.
OPENAI_API_KEY = OPENROUTER_API_KEY
BASE_URL = OPENROUTER_BASE_URL


def create_openrouter_client() -> AsyncOpenAI | None:
    """Create AsyncOpenAI client pointed at the OpenRouter endpoint."""
    api_key = (OPENROUTER_API_KEY or "").strip()
    if not api_key:
        logger.warning("OpenRouter client is not configured: missing AGENTS__OPENROUTER_API_KEY")
        return None

    try:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            http_client=_make_http_client(),
            default_headers={
                "HTTP-Referer": "https://gpthub.app",
                "X-Title": "GPTHub",
            },
        )
        set_default_openai_key(api_key)
        set_default_openai_client(client)
        set_tracing_disabled(disabled=True)
        return client
    except Exception:
        logger.exception("Failed to initialize OpenRouter client")
        return None


try:
    OPENROUTER_CLIENT = create_openrouter_client()
except Exception:
    OPENROUTER_CLIENT = None

# Backward-compatible alias so the facade can address us uniformly.
OPENAI_CLIENT = OPENROUTER_CLIENT


def get_openai_client() -> AsyncOpenAI | None:
    return OPENROUTER_CLIENT


def _models_cache_ttl() -> int:
    ttl = config.agents.openrouter_models_cache_ttl_sec or DEFAULT_MODELS_CACHE_TTL_SEC
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
    """List models from the OpenRouter API (cached, MWS-compatible signature)."""
    target_client = client or OPENROUTER_CLIENT
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
            logger.exception("Failed to fetch available models from OpenRouter API")
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
    """Call OpenRouter chat completions endpoint (/v1/chat/completions)."""
    target_client = client or OPENROUTER_CLIENT
    if target_client is None:
        raise RuntimeError("OpenRouter client is not configured")

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
    """Call OpenRouter completions endpoint (/v1/completions)."""
    target_client = client or OPENROUTER_CLIENT
    if target_client is None:
        raise RuntimeError("OpenRouter client is not configured")

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
    """Call OpenRouter embeddings endpoint (/v1/embeddings)."""
    target_client = client or OPENROUTER_CLIENT
    if target_client is None:
        raise RuntimeError("OpenRouter client is not configured")
    return await target_client.embeddings.create(model=model, input=text)


def clear_models_cache() -> None:
    _MODELS_CACHE["items"] = []
    _MODELS_CACHE["expires_at"] = 0.0
