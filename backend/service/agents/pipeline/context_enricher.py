"""Context enrichment helpers for agent pipeline."""

from __future__ import annotations

import asyncio
from typing import Any, Optional, Union


async def load_memory_context(user_id: Optional[Union[int, str]], logger) -> str:
    """Load user memory context from MemoryService.

    Returns an empty string if user id is missing or retrieval fails.
    """
    if not user_id:
        return ""

    try:
        from service.analytics.application.memory_service import MemoryService

        mem_svc = MemoryService()
        return await mem_svc.get_memory_context(str(user_id))
    except Exception:
        logger.debug("Memory context loading failed", exc_info=True)
        return ""


def _trim_to_max_chars(text: str, max_chars: int | None) -> str:
    if max_chars is None or max_chars <= 0:
        return text
    if len(text) <= max_chars:
        return text

    marker = "\n...[context truncated]"
    if max_chars <= len(marker) + 1:
        return text[:max_chars]
    return text[: max_chars - len(marker)] + marker


async def load_session_history_context(
    session: Optional[Any],
    logger,
    *,
    limit_messages: int = 8,
    max_chars: int = 4000,
) -> str:
    """Load recent chat history from session and format it for prompt context."""
    if session is None or limit_messages <= 0:
        return ""

    get_items = getattr(session, "get_items", None)
    if not callable(get_items):
        return ""

    try:
        try:
            items = await get_items(limit=limit_messages)
        except TypeError:
            items = await get_items()
    except Exception:
        logger.debug("Session history loading failed", exc_info=True)
        return ""

    if not isinstance(items, list) or not items:
        return ""

    role_map = {
        "user": "Пользователь",
        "assistant": "Ассистент",
        "system": "Система",
    }
    rendered: list[str] = []
    for item in items[-limit_messages:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip().lower()
        content = str(item.get("content") or "").strip()
        if role not in role_map or not content:
            continue
        rendered.append(f"- {role_map[role]}: {content}")

    if not rendered:
        return ""

    context_block = (
        "## История чата (последние сообщения)\n"
        "Используй факты из этой истории как источник истины для ссылок на прошлые реплики "
        "(например: имя пользователя, явные предпочтения, ранее данные ответы).\n"
        "Если вопрос относится к прошлым репликам — отвечай на основе этой истории.\n\n"
        + "\n".join(rendered)
    )
    return _trim_to_max_chars(context_block, max_chars)


def build_effective_input(
    user_input: str,
    *,
    memory_context: str = "",
    chat_history_context: str = "",
    file_context: Optional[str] = None,
    max_context_chars: Optional[int] = None,
) -> str:
    """Build one-shot effective input by appending extra context sections."""
    user_input = str(user_input or "")
    extra_context: list[str] = []
    if memory_context:
        extra_context.append(memory_context)
    if chat_history_context:
        extra_context.append(chat_history_context)
    if file_context:
        extra_context.append(f"## Контекст из загруженного файла:\n{file_context}")

    if not extra_context:
        return _trim_to_max_chars(user_input, max_context_chars)

    context_blob = "\n\n".join(extra_context)

    # Prefer preserving latest user input; trim supplemental context first.
    if max_context_chars and max_context_chars > 0:
        remaining_budget = max_context_chars - len(user_input) - 2
        if remaining_budget <= 0:
            return _trim_to_max_chars(user_input, max_context_chars)
        context_blob = _trim_to_max_chars(context_blob, remaining_budget)

    combined = f"{user_input}\n\n{context_blob}"
    return _trim_to_max_chars(combined, max_context_chars)


def schedule_memory_extraction(user_id: str, thread_id: str, last_message: str, logger) -> None:
    """Schedule background memory extraction (fire-and-forget)."""

    async def _extract():
        try:
            from service.analytics.application.memory_service import MemoryService

            svc = MemoryService()
            messages = [{"role": "user", "content": last_message}]
            await svc.extract_and_save_facts(user_id, thread_id, messages)
        except Exception:
            logger.debug("Background memory extraction failed", exc_info=True)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_extract())
    except RuntimeError:
        # No running loop in current context; skip scheduling.
        pass
