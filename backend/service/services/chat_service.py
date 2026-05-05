import logging
from typing import Any

from service.services.chat_contracts import (
    ChatProcessingMetadata,
    ChatReplyResult,
    ChatRequestContext,
    ChatRouteDecision,
    build_provider_unavailable_reply,
)
from service.services.chat_exceptions import ChatErrorMapper, JobOrchestrationError, ModelRoutingError
from service.services.chat_fallback_service import ChatFallbackService
from service.services.chat_job_orchestrator import ChatJobOrchestrator
from service.services.chat_persistence_service import ChatPersistenceService
from service.services.model_routing_service import ModelRoutingService

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, repository=None, agent=None, job_handler=None):
        self.persistence_service = ChatPersistenceService(repository=repository)
        self.routing_service = ModelRoutingService()
        if job_handler is None:
            from service import container

            job_handler = container.get_current_container().services.process_chat_message_handler
        self.job_orchestrator = ChatJobOrchestrator(handler=job_handler)
        self.fallback_service = ChatFallbackService(agent=agent)

    async def create_thread(
        self,
        user_id: str | int | None,
        title: str | None,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        return await self.persistence_service.create_thread(user_id=user_id, title=title, thread_id=thread_id)

    async def post_message(self, context: ChatRequestContext) -> ChatReplyResult:
        route_decision = ChatRouteDecision(
            selected_model=context.selected_model,
            web_search=context.web_search,
            deep_research=context.deep_research,
            route_override=context.route_override,
        )

        try:
            route_decision = await self.routing_service.resolve_route(
                text=context.text,
                selected_model=context.selected_model,
                input_type=context.input_type,
                web_search=context.web_search,
                deep_research=context.deep_research,
                route_override=context.route_override,
            )
        except ModelRoutingError as exc:
            logger.warning("Model routing failed: %s", exc)

        try:
            result = await self.job_orchestrator.execute(
                thread_id=context.thread_id,
                text=context.text,
                user_id=context.user_id,
                selected_model=route_decision.selected_model,
                input_type=context.input_type,
                web_search=route_decision.web_search,
                deep_research=route_decision.deep_research,
                file_context=context.file_context,
                route_override=route_decision.route_override,
            )
<<<<<<< HEAD
            # Auto-activate route/tool from LLM router when user hasn't set them explicitly
            if not web_search and not deep_research and not route_override:
                auto_tool = routing_meta.get("tool", "none")
                if auto_tool == "web_search":
                    web_search = True
                    logger.info("Router auto-activated web_search")
                elif auto_tool == "deep_research":
                    deep_research = True
                    logger.info("Router auto-activated deep_research")
                elif auto_tool in {"audio_transcribe", "image_gen", "pptx_gen", "general"}:
                    route_override = auto_tool
                    logger.info("Router auto-selected route_override=%s", auto_tool)
        except Exception:
            logger.exception("Failed to resolve routed model, continuing with provided model")
=======
        except JobOrchestrationError as exc:
            logger.warning("Job orchestration failed, fallback to direct agent path: %s", exc)
            result = await self.fallback_service.execute(
                thread_id=context.thread_id,
                text=context.text,
                user_id=context.user_id,
                selected_model=route_decision.selected_model,
                input_type=context.input_type,
                web_search=route_decision.web_search,
                deep_research=route_decision.deep_research,
                file_context=context.file_context,
                route_override=route_decision.route_override,
            )
            result.metadata = result.metadata.merged({"error_code": ChatErrorMapper.to_code(exc)})

        if route_decision.routing_metadata:
            result.metadata = result.metadata.merged({"model_routing": route_decision.routing_metadata})
>>>>>>> 3673cd22f63efeba7dd6dbba3c163d7e24f27f58

        try:
            await self.persistence_service.persist_messages(context.thread_id, context.text, result.reply, context.user_id)
        except Exception:
            logger.debug("Failed to persist messages", exc_info=True)

        if not str(result.reply).strip():
            provider_error = result.metadata.data.get("provider_error")
            result.reply = build_provider_unavailable_reply(provider_error)
            result.metadata = ChatProcessingMetadata(
                data={
                    **result.metadata.data,
                    "provider_unavailable": True,
                    **({"provider_error": provider_error} if provider_error else {}),
                }
            )

        return result

    async def get_messages(self, thread_id: str, page: int = 1, per_page: int = 50) -> dict[str, Any]:
        return await self.persistence_service.get_messages(thread_id=thread_id, page=page, per_page=per_page)

    async def list_threads(self, user_id: str | int | None = None, page: int = 1, per_page: int = 50) -> dict[str, Any]:
        return await self.persistence_service.list_threads(user_id=user_id, page=page, per_page=per_page)

    async def delete_thread(self, thread_id: str) -> bool:
        return await self.persistence_service.delete_thread(thread_id)
