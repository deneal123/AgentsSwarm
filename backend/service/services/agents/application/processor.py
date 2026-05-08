"""Main entry point for agent system — unified streaming processor."""
import logging
from typing import AsyncGenerator, Optional, Any

from service.services.agents.domain.events import AgentEvent
from service.services.agents.application.orchestrator import Orchestrator
from service.services.agents.pipeline.event_stream import EventSequencer
from service.services.agents.pipeline import (
    build_effective_input,
    build_processing_error_event,
    build_user_context,
    load_memory_context,
    load_session_history_context,
    resolve_agent_route,
    run_post_response_hooks,
)
from service.settings import config

# Import unified client facade to initialize configured provider (MWS/OpenAI)
from service.services.agents import client as agents_client  # noqa: F401

logger = logging.getLogger(__name__)


class AgentProcessor:
    """Main entry point for agent system.

    Provides unified async streaming interface that yields AgentEvent objects.
    """

    def __init__(self, model_settings: dict = None):
        self.orchestrator = Orchestrator(model_settings)

    async def process_message_stream(
        self,
        user_input: str,
        thread_id: str,
        user_id: Optional[int] = None,
        session: Optional[Any] = None,
        *,
        route_override: Optional[str] = None,
        input_type: Optional[str] = None,
        web_search: bool = False,
        deep_research: bool = False,
        file_context: Optional[str] = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Process user message and yield events."""
        stream = EventSequencer()

        try:
            context = build_user_context(user_id=user_id, session=session, thread_id=thread_id)

            agent_name, routing_start, routing_complete = await resolve_agent_route(
                orchestrator=self.orchestrator,
                user_input=user_input,
                thread_id=thread_id,
                route_override=route_override,
                input_type=input_type,
                web_search=web_search,
                deep_research=deep_research,
            )
            yield stream.attach(routing_start)
            yield stream.attach(routing_complete)

            memory_context = await load_memory_context(user_id, logger)
            chat_history_context = await load_session_history_context(
                session,
                logger,
                limit_messages=config.agents.chat_history_messages_limit,
                max_chars=config.agents.max_context_chars,
            )

            agent = self.orchestrator.get_agent(agent_name)

            effective_input = build_effective_input(
                user_input,
                memory_context=memory_context,
                chat_history_context=chat_history_context,
                file_context=file_context,
                max_context_chars=config.agents.max_context_chars,
            )

            async for event in agent.process(effective_input, context):
                yield stream.attach(event)

            run_post_response_hooks(
                user_id=user_id,
                thread_id=thread_id,
                user_input=user_input,
                logger=logger,
            )

        except Exception as exc:
            yield stream.attach(build_processing_error_event(exc, thread_id=thread_id, logger=logger))
