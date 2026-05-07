from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from service.chat.application.chat_application_service import ChatApplicationService
from service.chat.domain.chat_fallback_service import ChatFallbackService
from service.chat.domain.chat_job_orchestrator import ChatJobOrchestrator
from service.chat.domain.chat_service import ChatService
from service.chat.persistence.chat_persistence_service import ChatPersistenceService
from service.agents.application.model_routing_service import ModelRoutingService


@dataclass(slots=True)
class ChatComponents:
    routing_service: ModelRoutingService
    orchestration_service: ChatJobOrchestrator
    persistence_service: ChatPersistenceService
    fallback_service: ChatFallbackService
    chat_service: ChatService
    application_service: ChatApplicationService


def build_chat_components(*, repository: Any, job_handler: Any, file_service: Any, agent: Any = None) -> ChatComponents:
    routing_service = ModelRoutingService()
    orchestration_service = ChatJobOrchestrator(handler=job_handler)
    persistence_service = ChatPersistenceService(repository=repository)
    fallback_service = ChatFallbackService(agent=agent, file_service=file_service)
    chat_service = ChatService(
        routing_service=routing_service,
        orchestration_service=orchestration_service,
        persistence_service=persistence_service,
        fallback_service=fallback_service,
    )
    application_service = ChatApplicationService(chat_service=chat_service, file_service=file_service)
    return ChatComponents(
        routing_service=routing_service,
        orchestration_service=orchestration_service,
        persistence_service=persistence_service,
        fallback_service=fallback_service,
        chat_service=chat_service,
        application_service=application_service,
    )
