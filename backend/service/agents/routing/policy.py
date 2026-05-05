"""Routing policy helpers.

Отделяет policy-решения (приоритет флагов, input-type override, fallback)
от исполнения router-agent.
"""

from typing import Optional


_ALLOWED_FORCED_CATEGORIES = {"deep_research", "web_search", "audio_transcribe", "image_gen", "pptx_gen", "general"}


def resolve_forced_category(
    *,
    route_override: Optional[str],
    input_type: Optional[str],
    web_search: bool,
    deep_research: bool,
) -> Optional[str]:
    """Return category forced by upstream flags/input type, if any."""
    if route_override and route_override in _ALLOWED_FORCED_CATEGORIES:
        return route_override
    if input_type == "audio":
        return "audio_transcribe"
    if deep_research:
        return "deep_research"
    if web_search:
        return "web_search"
    # Uploaded image input means analysis, not image generation.
    if input_type == "image":
        return "general"
    return None


def finalize_category(llm_category: Optional[str]) -> str:
    """Finalize category with safe fallback."""
    return llm_category or "general"
