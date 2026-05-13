"""Unified facade for LLM clients used by agents.

Здесь живёт общий API (`create_chat_completion`, `list_available_models`, ...),
который под капотом делегирует в MWS-, OpenAI- или OpenRouter-клиент
в зависимости от конфигурации. Провайдер-специфичные модули доступны как
`service.services.agents.domain.client.mws_client`, `service.services.agents.domain.client.openai_client` и
`service.services.agents.domain.client.openrouter_client`.
"""

import logging

from service.settings import config

from . import mws_client, openai_client, openrouter_client

logger = logging.getLogger(__name__)


try:
    from agents import set_default_openai_client, set_default_openai_key, set_tracing_disabled
except Exception:  # pragma: no cover - fallback for minimal envs without Agents SDK

    def set_default_openai_client(_client):
        return None

    def set_default_openai_key(_key):
        return None

    def set_tracing_disabled(*, disabled: bool):
        return None


def _select_active_provider():
    """Выбрать активного провайдера для high-level API.

    Правило по умолчанию:
    - если сконфигурирован MWS (ключ / base_url), используем его;
    - иначе, если есть ключ OpenAI — используем нативный OpenAI;
    - иначе, если есть ключ OpenRouter — используем OpenRouter;
    - иначе — MWS как заглушку (вызовы упадут с понятной ошибкой).
    """
    agents_cfg = config.agents
    provider = (agents_cfg.llm_provider or "auto").strip().lower()

    if provider == "mws":
        return mws_client
    if provider == "openai":
        return openai_client
    if provider == "openrouter":
        return openrouter_client

    # auto
    if agents_cfg.mws_api_key or agents_cfg.mws_base_url:
        return mws_client
    if agents_cfg.openai_api_key or agents_cfg.openai_base_url:
        return openai_client
    if agents_cfg.openrouter_api_key:
        return openrouter_client
    return mws_client


def _bind_agents_sdk_defaults(active_module) -> None:
    """Bind OpenAI Agents SDK defaults to the selected provider only.

    This avoids side effects when both provider modules are imported and each
    tries to set global SDK defaults at import time.
    """
    try:
        client = getattr(active_module, "OPENAI_CLIENT", None)
        api_key = getattr(active_module, "OPENAI_API_KEY", None)
        if client is not None:
            set_default_openai_client(client)
        if api_key:
            set_default_openai_key(str(api_key))
        set_tracing_disabled(disabled=True)
    except Exception:
        logger.debug("Failed to bind Agents SDK defaults for active provider", exc_info=True)


_ACTIVE = _select_active_provider()
if _ACTIVE is mws_client:
    ACTIVE_PROVIDER = "mws"
elif _ACTIVE is openai_client:
    ACTIVE_PROVIDER = "openai"
else:
    ACTIVE_PROVIDER = "openrouter"
_bind_agents_sdk_defaults(_ACTIVE)


async def create_chat_completion(*args, **kwargs):
    """Создать chat completion через активного провайдера."""
    return await _ACTIVE.create_chat_completion(*args, **kwargs)


async def create_completion(*args, **kwargs):
    """Создать completion через активного провайдера."""
    return await _ACTIVE.create_completion(*args, **kwargs)


async def create_embedding(*args, **kwargs):
    """Создать embedding через активного провайдера."""
    return await _ACTIVE.create_embedding(*args, **kwargs)


async def list_available_models(*args, **kwargs) -> list[str]:
    """Список моделей от активного провайдера (с кешированием)."""
    return await _ACTIVE.list_available_models(*args, **kwargs)


def get_openai_client():
    """Вернуть низкоуровневый клиент активного провайдера."""
    if hasattr(_ACTIVE, "get_openai_client"):
        return _ACTIVE.get_openai_client()
    # Для нативного OpenAI такого helper'а нет — используем OPENAI_CLIENT.
    return openai_client.OPENAI_CLIENT


def clear_models_cache() -> None:
    """Очистить кеш моделей активного провайдера (если он его поддерживает)."""
    if hasattr(_ACTIVE, "clear_models_cache"):
        return _ACTIVE.clear_models_cache()
    return None


def get_active_provider() -> str:
    """Return active provider name: 'mws', 'openai', or 'openrouter'."""
    return ACTIVE_PROVIDER


# Для совместимости с существующим кодом и SDK: ссылка на клиент активного
# провайдера.
OPENAI_CLIENT = getattr(_ACTIVE, "OPENAI_CLIENT", None)


__all__ = [
    "OPENAI_CLIENT",
    "create_chat_completion",
    "create_completion",
    "create_embedding",
    "get_openai_client",
    "list_available_models",
    "clear_models_cache",
    "get_active_provider",
    "ACTIVE_PROVIDER",
]
