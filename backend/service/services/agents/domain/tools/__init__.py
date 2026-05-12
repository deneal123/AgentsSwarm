"""Tooling package for agent-executable capabilities."""

from service.services.agents.domain.tools.router import route_model
from service.services.agents.domain.tools.web_search import parse_url, web_search, web_search_and_summarize
from service.services.agents.domain.tools.deep_research import deep_research
from service.services.agents.domain.tools.pptx import generate_pptx
from service.services.agents.domain.tools.function_tools import DEFAULT_FUNCTION_TOOLS

__all__ = [
    "route_model",
    "web_search",
    "parse_url",
    "web_search_and_summarize",
    "deep_research",
    "generate_pptx",
    "DEFAULT_FUNCTION_TOOLS",
]
