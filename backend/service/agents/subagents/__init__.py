"""Sub-agents package."""

from .audio_transcribe import AudioTranscriptionAgent
from .base import BaseSubAgent
from .deep_research import DeepResearchAgent
from .factory import build_subagents
from .general import GeneralAgent
from .image_generation import ImageGenerationAgent
from .pptx_generation import PPTXGenerationAgent
from .web_search import WebSearchAgent

__all__ = [
    "BaseSubAgent",
    "build_subagents",
    "GeneralAgent",
    "AudioTranscriptionAgent",
    "WebSearchAgent",
    "DeepResearchAgent",
    "ImageGenerationAgent",
    "PPTXGenerationAgent",
]
