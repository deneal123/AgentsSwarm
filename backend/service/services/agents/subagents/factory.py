"""Factory helpers for sub-agent composition."""

from typing import Optional

from service.services.agents.domain.base import BaseAgent
from service.services.agents.subagents.audio_transcribe import AudioTranscriptionAgent
from service.services.agents.subagents.deep_research import DeepResearchAgent
from service.services.agents.subagents.general import GeneralAgent
from service.services.agents.subagents.image_generation import ImageGenerationAgent
from service.services.agents.subagents.pptx_generation import PPTXGenerationAgent
from service.services.agents.subagents.web_search import WebSearchAgent


def build_subagents(model_settings: Optional[dict] = None) -> dict[str, BaseAgent]:
    """Build and return the default sub-agent registry."""
    settings = model_settings or {}
    general = GeneralAgent(settings)

    return {
        "general": general,
        "audio_transcribe": AudioTranscriptionAgent(settings),
        "web_search": WebSearchAgent(settings),
        "deep_research": DeepResearchAgent(settings),
        "image_gen": ImageGenerationAgent(settings),
        "pptx_gen": PPTXGenerationAgent(settings),
    }
