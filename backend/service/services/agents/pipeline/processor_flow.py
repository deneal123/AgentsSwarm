"""Flow helpers for AgentProcessor orchestration steps."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, Tuple

from service.services.agents.events import AgentEvent, EventType
from service.services.agents.pydantic.agents import UserContext


def build_user_context(*, user_id: Optional[int], session: Optional[Any], thread_id: str) -> UserContext:
    """Build normalized user context for downstream agents."""
    return UserContext(
        user_id=str(user_id or ""),
        request_time=datetime.now(timezone.utc),
        session=session,
        thread_id=thread_id,
    )


async def resolve_agent_route(
    *,
    orchestrator,
    user_input: str,
    thread_id: str,
    route_override: Optional[str],
    input_type: Optional[str],
    web_search: bool,
    deep_research: bool,
) -> Tuple[str, AgentEvent, AgentEvent]:
    """Resolve route and return route events (without sequence numbers)."""
    routing_start = AgentEvent(
        type=EventType.ROUTING_START,
        data="Определяю подходящего агента...",
    )

    agent_name = await orchestrator.route(
        user_input,
        thread_id,
        route_override=route_override,
        input_type=input_type,
        web_search=web_search,
        deep_research=deep_research,
    )

    routing_complete = AgentEvent(
        type=EventType.ROUTING_COMPLETE,
        agent_name=agent_name,
        data=f"Выбран агент: {agent_name}",
        metadata={"agent_type": agent_name},
    )

    return agent_name, routing_start, routing_complete
