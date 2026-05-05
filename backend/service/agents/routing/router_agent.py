"""LLM router-agent helpers."""

from typing import Any, Optional

from service.agents.client import get_active_provider
from service.agents.pydantic.agents import RoutingDecision
from service.agents.routing.constants import ALLOWED_CATEGORIES, ROUTER_PROMPT
from service.agents.tools.router import route_model


def create_router_agent(model_settings: Optional[dict], logger) -> Any:
    """Build SDK router agent or return None if SDK is unavailable."""
    try:
        from agents import Agent as SDKAgent, ModelSettings

        ms = ModelSettings(**(model_settings or {})) if isinstance(model_settings, dict) else model_settings
        return SDKAgent(
            name="router",
            instructions=ROUTER_PROMPT,
            model_settings=ms,
            output_type=RoutingDecision,
        )
    except Exception:
        logger.exception("Orchestrator: failed to init LLM router, fallback will be 'general'")
        return None


def extract_category(obj: Any) -> Optional[str]:
    """Extract route category from dict/object-like router output."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        category = obj.get("category")
        return category if isinstance(category, str) else None
    category = getattr(obj, "category", None)
    return category if isinstance(category, str) else None


async def resolve_category(router_agent: Any, user_input: str, logger) -> Optional[str]:
    """Resolve category by running router agent once."""
    # MWS in this project can reject SDK /responses while allowing chat/completions.
    # Route directly via chat-completions-based helper to avoid 403 noise and latency.
    if get_active_provider() == "mws":
        try:
            _model, meta = await route_model(
                text=user_input,
                selected_model=None,
                input_type=None,
            )
            tool = str((meta or {}).get("tool") or "none").strip().lower()
            mapped = {
                "none": "general",
                "general": "general",
                "web_search": "web_search",
                "deep_research": "deep_research",
                "audio_transcribe": "audio_transcribe",
                "image_gen": "image_gen",
                "pptx_gen": "pptx_gen",
            }.get(tool)
            return mapped if mapped in ALLOWED_CATEGORIES else None
        except Exception:
            logger.exception("Orchestrator: MWS route_model failed, fallback to general")
            return None

    if router_agent is None:
        return None

    try:
        from agents import Runner as SDKRunner

        result = await SDKRunner.run(router_agent, user_input, max_turns=1)
        out = getattr(result, "final_output", None) or result
        category = extract_category(out)
        return category if category in ALLOWED_CATEGORIES else None
    except Exception:
        logger.exception("Orchestrator: LLM router failed, fallback to general")
        return None
