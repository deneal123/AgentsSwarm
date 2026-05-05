"""Factory helpers for sub-agent composition."""

from typing import Optional

from service.agents.base_agent import BaseAgent
from service.agents.subagents.audio_transcribe import AudioTranscriptionAgent
from service.agents.subagents.deep_research import DeepResearchAgent
from service.agents.subagents.general import GeneralAgent
from service.agents.subagents.image_generation import ImageGenerationAgent
from service.agents.subagents.pptx_generation import PPTXGenerationAgent
from service.agents.subagents.web_search import WebSearchAgent


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
