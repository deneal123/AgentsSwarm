import logging
from typing import Any

from service.services.chat_contracts import ChatRouteDecision
from service.services.chat_exceptions import ModelRoutingError

logger = logging.getLogger(__name__)


class ModelRoutingService:
    async def resolve_route(
        self,
        text: str,
        selected_model: str | None,
        input_type: str | None,
        web_search: bool,
        deep_research: bool,
        route_override: str | None,
    ) -> ChatRouteDecision:
        try:
            from service.agents.tools.router import route_model

            effective_model, routing_meta = await route_model(
                text=text,
                selected_model=selected_model,
                input_type=input_type,
            )
        except Exception as exc:
            raise ModelRoutingError("Failed to resolve model route") from exc

        resolved_web_search = web_search
        resolved_deep_research = deep_research
        resolved_route_override = route_override

        if not web_search and not deep_research and not route_override:
            auto_tool = routing_meta.get("tool", "none")
            if auto_tool == "web_search":
                resolved_web_search = True
            elif auto_tool == "deep_research":
                resolved_deep_research = True
            elif auto_tool in {"audio_transcribe", "image_gen", "pptx_gen", "general"}:
                resolved_route_override = auto_tool

        return ChatRouteDecision(
            selected_model=effective_model,
            routing_metadata=dict(routing_meta or {}),
            web_search=resolved_web_search,
            deep_research=resolved_deep_research,
            route_override=resolved_route_override,
        )
