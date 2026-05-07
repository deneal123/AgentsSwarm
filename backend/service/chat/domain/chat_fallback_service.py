import logging
import time
from typing import Any

from service.chat.domain.chat_contracts import ChatProcessingMetadata, ChatReplyResult, build_provider_unavailable_reply

logger = logging.getLogger(__name__)


class ChatFallbackService:
    def __init__(self, agent=None):
        if agent is None:
            from service.agents.chat_agent import ChatAgent

            self.agent = ChatAgent()
        else:
            self.agent = agent

    async def execute(
        self,
        thread_id: str,
        text: str,
        user_id: str | int | None,
        selected_model: str | None,
        input_type: str | None,
        web_search: bool,
        deep_research: bool,
        file_context: str,
        route_override: str | None,
    ) -> ChatReplyResult:
        if web_search or deep_research or file_context or route_override:
            return await self._tool_path(
                thread_id=thread_id,
                text=text,
                user_id=user_id,
                selected_model=selected_model,
                input_type=input_type,
                web_search=web_search,
                deep_research=deep_research,
                file_context=file_context,
                route_override=route_override,
            )

        start = time.perf_counter()
        if selected_model:
            from service.agents.chat_agent import ChatAgent

            agent = ChatAgent(config={"model_settings": {"model": selected_model}})
            result = await agent.handle_message(thread_id, text, user_id)
        else:
            result = await self.agent.handle_message(thread_id, text, user_id)
        _latency = time.perf_counter() - start

        if isinstance(result, ChatReplyResult):
            metadata = result.metadata.data
            reply = str(result.reply or "")
            response_thread_id = str(result.thread_id or thread_id)
        else:
            metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
            reply = str(result.get("reply") or "")
            response_thread_id = str(result.get("thread_id") or thread_id)
        if not reply.strip():
            provider_error = metadata.get("error")
            reply = build_provider_unavailable_reply(provider_error)
            metadata = {
                **metadata,
                "provider_unavailable": True,
                **({"provider_error": provider_error} if provider_error else {}),
            }

        return ChatReplyResult(
            reply=reply,
            thread_id=response_thread_id,
            metadata=ChatProcessingMetadata(data=metadata),
        )

    async def _tool_path(
        self,
        thread_id: str,
        text: str,
        user_id: str | int | None,
        selected_model: str | None,
        input_type: str | None,
        web_search: bool,
        deep_research: bool,
        file_context: str,
        route_override: str | None,
    ) -> ChatReplyResult:
        from service.agents.events import EventType
        from service.agents.processor import AgentProcessor

        model_settings = {"model": selected_model} if selected_model else {}
        processor = AgentProcessor(model_settings=model_settings)

        reply_parts: list[str] = []
        error_messages: list[str] = []
        processor_metadata: dict[str, Any] = {}
        async for event in processor.process_message_stream(
            user_input=text,
            thread_id=thread_id,
            user_id=user_id,
            session=None,
            route_override=route_override,
            input_type=input_type,
            web_search=web_search,
            deep_research=deep_research,
            file_context=file_context,
        ):
            if event.type == EventType.STREAM_CHUNK and event.data:
                reply_parts.append(str(event.data))
            elif event.type == EventType.ERROR and event.data:
                error_messages.append(str(event.data))
            if event.metadata:
                processor_metadata.update(event.metadata)

        reply_text = "".join(reply_parts)
        if not reply_text.strip():
            provider_error = error_messages[0] if error_messages else None
            reply_text = build_provider_unavailable_reply(provider_error)
            processor_metadata = {
                **processor_metadata,
                "provider_unavailable": True,
                **({"provider_error": provider_error} if provider_error else {}),
            }

        file_url = None
        try:
            from service import container

            file_service = container.get_current_container().services.file_saver_service
            from service.services.agent_file_bridge import persist_generated_artifacts

            generated_file_url, processor_metadata = await persist_generated_artifacts(
                file_service=file_service,
                user_id=user_id,
                metadata=processor_metadata,
                job_id=thread_id,
            )
            file_url = generated_file_url
        except Exception:
            logger.debug("Failed to persist generated artifacts in fallback", exc_info=True)

        processor_metadata = {
            **processor_metadata,
            "fallback_tool_path": {
                "web_search": web_search,
                "deep_research": deep_research,
                "route_override": route_override,
                "has_file_context": bool(file_context),
            },
        }

        return ChatReplyResult(
            reply=reply_text,
            thread_id=thread_id,
            file_url=file_url,
            metadata=ChatProcessingMetadata(data=processor_metadata),
        )
