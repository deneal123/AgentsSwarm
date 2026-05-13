"""Reusable Agent SDK tools for GPTHub assistants."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from agents import FunctionTool, RunContextWrapper

logger = logging.getLogger(__name__)


def _context_dict(ctx: RunContextWrapper) -> dict:
    context = getattr(ctx, "context", None)
    if context is None:
        return {}
    if isinstance(context, dict):
        return context
    try:
        if hasattr(context, "model_dump"):
            return context.model_dump()
        if hasattr(context, "dict"):
            return context.dict()
    except Exception:
        logger.debug("Failed to dump tool context", exc_info=True)
    return {"raw_context": str(context)}


async def fetch_runtime_context_tool(ctx: RunContextWrapper, args: str) -> str:
    """Return normalized runtime context metadata for the current request."""
    payload = _context_dict(ctx)
    now = datetime.now(UTC).isoformat()
    result = {
        "timestamp_utc": now,
        "user_id": payload.get("user_id"),
        "thread_id": payload.get("thread_id") or payload.get("session_id"),
        "input_type": payload.get("input_type", "text"),
    }
    return json.dumps(result, ensure_ascii=False)


async def summarize_brief_tool(ctx: RunContextWrapper, args: str) -> str:
    """Create a deterministic brief summary from raw text provided in args."""
    text = ""
    try:
        parsed = json.loads(args) if isinstance(args, str) else args
        text = str((parsed or {}).get("text", ""))
    except Exception:
        text = str(args or "")

    cleaned = " ".join(text.split())
    if not cleaned:
        return "Нет текста для суммаризации."

    if len(cleaned) <= 240:
        return cleaned

    return cleaned[:240].rstrip() + "…"


fetch_runtime_context = FunctionTool(
    name="fetch_runtime_context",
    description="Получить системный контекст текущего запроса (user/thread/input_type).",
    params_json_schema={
        "type": "object",
        "properties": {},
    },
    on_invoke_tool=fetch_runtime_context_tool,
)

summarize_brief = FunctionTool(
    name="summarize_brief",
    description="Сделать краткое резюме переданного текста.",
    params_json_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
        },
        "required": ["text"],
    },
    on_invoke_tool=summarize_brief_tool,
)

DEFAULT_FUNCTION_TOOLS = [
    fetch_runtime_context,
    summarize_brief,
]
