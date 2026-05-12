from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from service.services.agents.application.processor import AgentProcessor
from service.services.agents.application.reply_assembler import ReplyAssembler
from service.services.agents.domain.events import EventType
from service.services.agents.domain.sessions import PseudoSession
from service.services.agents.domain.tools.router import route_model
from service.services.chat.domain.chat_contracts import build_provider_unavailable_reply


@dataclass(slots=True)
class RouteModelUseCase:
    async def execute(
        self, *, text: str, selected_model: str | None, input_type: str | None
    ) -> tuple[str | None, dict[str, Any]]:
        return await route_model(text=text, selected_model=selected_model, input_type=input_type)


@dataclass(slots=True)
class PrepareExecutionContextUseCase:
    def execute(
        self,
        *,
        routing_meta: dict[str, Any],
        route_override: str | None,
        web_search: bool,
        deep_research: bool,
        session_data: dict | None,
        thread_id: str,
        pseudo_session: Any | None,
    ) -> dict[str, Any]:
        if not web_search and not deep_research and not route_override:
            auto_tool = routing_meta.get("tool", "none")
            if auto_tool == "web_search":
                web_search = True
            elif auto_tool == "deep_research":
                deep_research = True
            elif auto_tool in {"audio_transcribe", "image_gen", "pptx_gen", "general"}:
                route_override = auto_tool
        return {
            "route_override": route_override,
            "web_search": web_search,
            "deep_research": deep_research,
            "pseudo_session": pseudo_session
            or PseudoSession(session_id=(session_data or {}).get("session_id", thread_id)),
        }


@dataclass(slots=True)
class RunAgentUseCase:
    async def execute(
        self,
        *,
        processor: AgentProcessor,
        reply_assembler: ReplyAssembler,
        metadata: dict[str, Any],
        **kwargs: Any,
    ) -> list[Any]:
        events = []
        async for event in processor.process_message_stream(**kwargs):
            events.append(event)
            if event.metadata:
                metadata.update(event.metadata)
            reply_assembler.consume(
                event=event,
                stream_chunk_type=EventType.STREAM_CHUNK,
                error_type=EventType.ERROR,
                structured_output_type=EventType.STRUCTURED_OUTPUT,
            )
        return events


@dataclass(slots=True)
class PostprocessAgentReplyUseCase:
    def execute(
        self, *, reply_assembler: ReplyAssembler, metadata: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        reply = reply_assembler.build_reply()
        metadata = {**metadata, **reply_assembler.metadata}
        if not str(reply).strip():
            provider_error = (
                reply_assembler.error_messages[0] if reply_assembler.error_messages else None
            )
            reply = build_provider_unavailable_reply(provider_error)
            metadata = {
                **metadata,
                "provider_unavailable": True,
                **({"provider_error": provider_error} if provider_error else {}),
            }
        return reply, metadata


@dataclass(slots=True)
class PersistSessionHistoryUseCase:
    def execute(
        self,
        *,
        reply: str,
        metadata: dict[str, Any],
        resolved_model: str,
        reply_assembler: ReplyAssembler,
        events: list[Any],
    ) -> dict[str, Any]:
        return {
            "reply": reply,
            "metadata": metadata,
            "resolved_model": resolved_model,
            "reply_parts_count": len(reply_assembler.reply_parts),
            "reply_chars_count": len(reply),
            "events": events,
        }
