from __future__ import annotations

from typing import Any

from service.services.agents.application.ports.interfaces import AgentExecutionPort
from service.services.agents.application.processor import AgentProcessor
from service.services.agents.application.reply_assembler import ReplyAssembler
from service.services.agents.application.use_cases.agent_execution_use_cases import (
    PersistSessionHistoryUseCase,
    PostprocessAgentReplyUseCase,
    PrepareExecutionContextUseCase,
    RouteModelUseCase,
    RunAgentUseCase,
)


class DefaultAgentExecutionService(AgentExecutionPort):
    async def execute(
        self,
        *,
        text: str,
        thread_id: str,
        user_id: str | None,
        session_data: dict | None,
        selected_model: str | None,
        route_override: str | None,
        input_type: str | None,
        web_search: bool,
        deep_research: bool,
        file_context: str,
        pseudo_session: Any | None = None,
    ) -> dict[str, Any]:
        resolved_model, routing_meta = await RouteModelUseCase().execute(
            text=text, selected_model=selected_model, input_type=input_type
        )
        context = PrepareExecutionContextUseCase().execute(
            routing_meta=routing_meta,
            route_override=route_override,
            web_search=web_search,
            deep_research=deep_research,
            session_data=session_data,
            thread_id=thread_id,
            pseudo_session=pseudo_session,
        )

        processor = AgentProcessor(
            model_settings={
                "model": resolved_model or "mws-gpt-alpha",
                "temperature": 0.7,
                "max_tokens": 1000,
            }
        )
        reply_assembler = ReplyAssembler()
        metadata: dict[str, Any] = {}
        if routing_meta:
            metadata["model_routing"] = routing_meta
            reply_assembler.metadata["model_routing"] = routing_meta

        events = await RunAgentUseCase().execute(
            processor=processor,
            reply_assembler=reply_assembler,
            metadata=metadata,
            user_input=text,
            thread_id=thread_id,
            user_id=user_id,
            session=context["pseudo_session"],
            route_override=context["route_override"],
            input_type=input_type,
            web_search=context["web_search"],
            deep_research=context["deep_research"],
            file_context=file_context,
        )
        reply, metadata = PostprocessAgentReplyUseCase().execute(
            reply_assembler=reply_assembler, metadata=metadata
        )
        return PersistSessionHistoryUseCase().execute(
            reply=reply,
            metadata=metadata,
            resolved_model=resolved_model or "mws-gpt-alpha",
            reply_assembler=reply_assembler,
            events=events,
        )
