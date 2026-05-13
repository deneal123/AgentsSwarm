"""GPTHub Orchestrator — LLM-first per-message intent routing."""

import logging

from service.services.agents.domain.base import BaseAgent
from service.services.agents.domain.routing import (
    create_router_agent,
    finalize_category,
    resolve_category,
    resolve_forced_category,
)
from service.services.agents.domain.subagents import build_subagents

logger = logging.getLogger(__name__)


class Orchestrator:
    """LLM-first per-message intent router.

    Priority:
      1. explicit flags from upstream (deep_research / web_search)
      2. LLM router output (RoutingDecision)
      3. safe fallback -> general
    """

    def __init__(self, model_settings: dict | None = None):
        self.model_settings = model_settings or {}
        self._agents: dict[str, BaseAgent] = build_subagents(self.model_settings)
        self._router_agent = create_router_agent(self.model_settings, logger)
        if self._router_agent is not None:
            logger.info("Orchestrator: LLM router initialized")

    async def route(
        self,
        user_input: str,
        thread_id: str | None = None,
        *,
        route_override: str | None = None,
        input_type: str | None = None,
        web_search: bool = False,
        deep_research: bool = False,
    ) -> str:
        forced_category = resolve_forced_category(
            route_override=route_override,
            input_type=input_type,
            web_search=web_search,
            deep_research=deep_research,
        )
        if forced_category:
            logger.info("Orchestrator: '%s...' -> %s (policy)", user_input[:60], forced_category)
            return forced_category

        category = await resolve_category(self._router_agent, user_input, logger)
        final_category = finalize_category(category)
        logger.info(
            "Orchestrator: '%s...' -> %s (%s)",
            user_input[:60],
            final_category,
            "llm" if category else "fallback",
        )
        return final_category

    def get_agent(self, agent_name: str) -> BaseAgent:
        """Return concrete agent for resolved route."""
        return self._agents.get(agent_name, self._agents["general"])
