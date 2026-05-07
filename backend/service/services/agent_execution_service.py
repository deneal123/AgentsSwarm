from __future__ import annotations

from typing import Any

from service.agents.events import EventType
from service.agents.processor import AgentProcessor
from service.agents.sessions import PseudoSession
from service.agents.tools.router import route_model
from service.infrastructure.messaging.agent_streaming import ReplyAssembler
from service.ports import AgentExecutionPort
from service.chat.domain.chat_contracts import build_provider_unavailable_reply


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
        resolved_model, routing_meta = await route_model(text=text, selected_model=selected_model, input_type=input_type)
        if not web_search and not deep_research and not route_override:
            auto_tool = routing_meta.get("tool", "none")
            if auto_tool == "web_search":
                web_search = True
            elif auto_tool == "deep_research":
                deep_research = True
            elif auto_tool in {"audio_transcribe", "image_gen", "pptx_gen", "general"}:
                route_override = auto_tool

        processor = AgentProcessor(model_settings={"model": resolved_model or "mws-gpt-alpha", "temperature": 0.7, "max_tokens": 1000})
        pseudo_session = pseudo_session or PseudoSession(session_id=(session_data or {}).get("session_id", thread_id))
        reply_assembler = ReplyAssembler()
        metadata: dict[str, Any] = {}
        if routing_meta:
            metadata["model_routing"] = routing_meta
            reply_assembler.metadata["model_routing"] = routing_meta

        events = []
        async for event in processor.process_message_stream(
            user_input=text,
            thread_id=thread_id,
            user_id=user_id,
            session=pseudo_session,
            route_override=route_override,
            input_type=input_type,
            web_search=web_search,
            deep_research=deep_research,
            file_context=file_context,
        ):
            events.append(event)
            if event.metadata:
                metadata.update(event.metadata)
            reply_assembler.consume(
                event=event,
                stream_chunk_type=EventType.STREAM_CHUNK,
                error_type=EventType.ERROR,
                structured_output_type=EventType.STRUCTURED_OUTPUT,
            )

        reply = reply_assembler.build_reply()
        metadata = {**metadata, **reply_assembler.metadata}
        if not str(reply).strip():
            provider_error = reply_assembler.error_messages[0] if reply_assembler.error_messages else None
            reply = build_provider_unavailable_reply(provider_error)
            metadata = {**metadata, "provider_unavailable": True, **({"provider_error": provider_error} if provider_error else {})}

        return {
            "reply": reply,
            "metadata": metadata,
            "resolved_model": resolved_model or "mws-gpt-alpha",
            "reply_parts_count": len(reply_assembler.reply_parts),
            "reply_chars_count": len(reply),
            "events": events,
        }
