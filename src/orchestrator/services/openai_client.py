"""Factory for OpenAI-compatible clients (OpenAI/vLLM) used by Agents SDK.

Environment-driven configuration only; constants stay in settings.

Vars:
- AGENTS_PROVIDER: "openai" (default) | "vllm"
- OPENAI_API_KEY: key for OpenAI cloud
- OPENAI_BASE_URL: optional override (default https://api.openai.com/v1)
- VLLM_BASE_URL: required when provider=vllm
- VLLM_API_KEY: optional token for vLLM deployments (sent as Bearer)
- PROXY_HOST/PROXY_PORT/PROXY_USER/PROXY_PASS: optional HTTP proxy
- AGENTS_TRACING_DISABLED: default "1" (true). Set "0" to enable tracing
"""

from __future__ import annotations

import os
import logging
import httpx
from openai import AsyncOpenAI
from agents import set_default_openai_client, set_default_openai_key, set_tracing_disabled

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
            return httpx.AsyncClient(proxies=proxy_url)
        except Exception:
            logger.exception("Failed to build proxy client; falling back to default HTTP client")
    return httpx.AsyncClient()


def build_openai_client() -> AsyncOpenAI:
    provider = os.getenv("AGENTS_PROVIDER", "openai").lower()
    tracing_disabled = os.getenv("AGENTS_TRACING_DISABLED", "1") != "0"

    if provider == "vllm":
        base_url = os.getenv("VLLM_BASE_URL")
        if not base_url:
            raise RuntimeError("VLLM_BASE_URL is required when AGENTS_PROVIDER=vllm")
        api_key = os.getenv("VLLM_API_KEY", "EMPTY")
        client = AsyncOpenAI(api_key=api_key, base_url=base_url, http_client=_make_http_client())
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
