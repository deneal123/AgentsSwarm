"""Factory for OpenAI-compatible clients (OpenAI/vLLM/OpenRouter) used by Agents SDK.

Environment-driven configuration only; constants stay in settings.

Vars:
- AGENTS_PROVIDER: "openai" (default) | "vllm" | "openrouter"
- OPENAI_API_KEY: key for OpenAI cloud
- OPENAI_BASE_URL: optional override (default https://api.openai.com/v1)
- VLLM_BASE_URL: required when provider=vllm
- VLLM_API_KEY: optional token for vLLM deployments (sent as Bearer)
- OPENROUTER_API_KEY: key for OpenRouter (https://openrouter.ai)
- OPENROUTER_BASE_URL: optional override (default https://openrouter.ai/api/v1)
- OPENROUTER_SITE_URL: optional X-Title / HTTP-Referer header value
- PROXY_HOST/PROXY_PORT/PROXY_USER/PROXY_PASS: optional HTTP proxy
- AGENTS_TRACING_DISABLED: default "1" (true). Set "0" to enable tracing
"""

from __future__ import annotations

import os
import logging
import httpx
from openai import AsyncOpenAI
from agents import set_default_openai_client, set_default_openai_key, set_tracing_disabled
from orchestrator.utils.env import env_bool

logger = logging.getLogger(__name__)


def _make_http_client() -> httpx.AsyncClient:
    proxy_host = os.getenv("PROXY_HOST")
    proxy_port = os.getenv("PROXY_PORT")
    proxy_user = os.getenv("PROXY_USER")
    proxy_pass = os.getenv("PROXY_PASS")

    if proxy_host and proxy_port:
        try:
            creds = f"{proxy_user or ''}:{proxy_pass or ''}@" if proxy_user or proxy_pass else ""
            proxy_url = f"http://{creds}{proxy_host}:{proxy_port}"
            return httpx.AsyncClient(proxy=proxy_url)
        except Exception:
            logger.exception("Failed to build proxy client; falling back to default HTTP client")
    return httpx.AsyncClient()


def build_openai_client() -> AsyncOpenAI:
    provider = os.getenv("AGENTS_PROVIDER", "openai").lower()
    tracing_disabled = env_bool("AGENTS_TRACING_DISABLED", True)

    if provider == "vllm":
        base_url = os.getenv("VLLM_BASE_URL")
        if not base_url:
            raise RuntimeError("VLLM_BASE_URL is required when AGENTS_PROVIDER=vllm")
        api_key = os.getenv("VLLM_API_KEY", "EMPTY")
        client = AsyncOpenAI(api_key=api_key, base_url=base_url, http_client=_make_http_client())
    elif provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required when AGENTS_PROVIDER=openrouter")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        site_url = os.getenv("OPENROUTER_SITE_URL", "")
        default_headers = {"HTTP-Referer": site_url} if site_url else {}
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=default_headers,
            http_client=_make_http_client(),
        )
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required when AGENTS_PROVIDER=openai")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        client = AsyncOpenAI(api_key=api_key, base_url=base_url, http_client=_make_http_client())

    try:
        set_default_openai_key(api_key)
        set_default_openai_client(client)
        set_tracing_disabled(disabled=tracing_disabled)
    except Exception:
        logger.exception("Failed to set defaults for Agents SDK")

    logger.info("OpenAI client initialized", extra={"provider": provider, "base_url": base_url})
    return client


__all__ = ["build_openai_client"]
