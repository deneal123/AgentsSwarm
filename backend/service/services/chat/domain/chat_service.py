import logging
from typing import Any

from service.services.chat.application.ports.chat_ports import ChatOrchestrationPort, ChatPersistencePort, ChatStreamingPort
from service.services.chat.domain.chat_contracts import (
    ChatProcessingMetadata,
    ChatReplyResult,
    ChatRequestContext,
    ChatRouteDecision,
    build_provider_unavailable_reply,
)
from service.services.chat.domain.chat_exceptions import ChatErrorMapper, JobOrchestrationError, ModelRoutingError

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self,
        routing_service: Any,
        orchestration_service: ChatOrchestrationPort,
        persistence_service: ChatPersistencePort,
        fallback_service: ChatStreamingPort,
    ):
        self.persistence_service = persistence_service
        self.routing_service = routing_service
        self.job_orchestrator = orchestration_service
        self.fallback_service = fallback_service

    async def create_thread(self, user_id: str | int | None, title: str | None, thread_id: str | None = None) -> dict[str, Any]:
        return await self.persistence_service.create_thread(user_id=user_id, title=title, thread_id=thread_id)

    async def post_message(self, context: ChatRequestContext) -> ChatReplyResult:
        route_decision = ChatRouteDecision(selected_model=context.selected_model, web_search=context.web_search, deep_research=context.deep_research, route_override=context.route_override)
        try:
            route_decision = await self.routing_service.resolve_route(text=context.text, selected_model=context.selected_model, input_type=context.input_type, web_search=context.web_search, deep_research=context.deep_research, route_override=context.route_override)
        except ModelRoutingError as exc:
            logger.warning("Model routing failed: %s", exc)
        try:
            result = await self.job_orchestrator.execute(thread_id=context.thread_id, text=context.text, user_id=context.user_id, selected_model=route_decision.selected_model, input_type=context.input_type, web_search=route_decision.web_search, deep_research=route_decision.deep_research, file_context=context.file_context, route_override=route_decision.route_override)
        except JobOrchestrationError as exc:
            logger.warning("Job orchestration failed, fallback to direct agent path: %s", exc)
            result = await self.fallback_service.execute(thread_id=context.thread_id, text=context.text, user_id=context.user_id, selected_model=route_decision.selected_model, input_type=context.input_type, web_search=route_decision.web_search, deep_research=route_decision.deep_research, file_context=context.file_context, route_override=route_decision.route_override)
            result.metadata = result.metadata.merged({"error_code": ChatErrorMapper.to_code(exc)})
        if route_decision.routing_metadata:
            result.metadata = result.metadata.merged({"model_routing": route_decision.routing_metadata})
        try:
            await self.persistence_service.persist_messages(context.thread_id, context.text, result.reply, context.user_id)
        except Exception:
            logger.debug("Failed to persist messages", exc_info=True)
        if not str(result.reply).strip():
            provider_error = result.metadata.data.get("provider_error")
            result.reply = build_provider_unavailable_reply(provider_error)
            result.metadata = ChatProcessingMetadata(data={**result.metadata.data, "provider_unavailable": True, **({"provider_error": provider_error} if provider_error else {})})
        return result

    async def get_messages(self, thread_id: str, page: int = 1, per_page: int = 50) -> dict[str, Any]:
        return await self.persistence_service.get_messages(thread_id=thread_id, page=page, per_page=per_page)

    async def list_threads(self, user_id: str | int | None = None, page: int = 1, per_page: int = 50) -> dict[str, Any]:
        return await self.persistence_service.list_threads(user_id=user_id, page=page, per_page=per_page)

    async def delete_thread(self, thread_id: str) -> bool:
        return await self.persistence_service.delete_thread(thread_id)
