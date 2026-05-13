from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from service.services.chat.domain.chat_contracts import ChatReplyResult, ChatRequestContext
from service.services.chat.domain.chat_service import ChatService


@dataclass(slots=True)
class CreateThreadUseCase:
    chat_service: ChatService

    async def execute(self, *, user_id: str | None, title: str | None) -> dict[str, Any]:
        return await self.chat_service.create_thread(user_id=user_id, title=title)


@dataclass(slots=True)
class PostMessageUseCase:
    chat_service: ChatService

    async def execute(self, *, thread_id: str, payload: Any) -> ChatReplyResult:
        return await self.chat_service.post_message(
            ChatRequestContext(
                thread_id=thread_id,
                text=payload.text,
                user_id=payload.user_id,
                selected_model=payload.model,
                route_override=payload.route_override,
                input_type=payload.input_type,
                web_search=payload.web_search,
                deep_research=payload.deep_research,
                file_context=payload.file_context,
            )
        )


@dataclass(slots=True)
class PersistChatMessagesUseCase:
    chat_service: ChatService

    async def execute(
        self, *, thread_id: str, user_text: str, assistant_text: str, user_id: str | None
    ) -> None:
        await self.chat_service.persistence_service.persist_messages(
            thread_id, user_text, assistant_text, user_id
        )


@dataclass(slots=True)
class StreamChatResponseUseCase:
    chat_service: ChatService

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        context = ChatRequestContext(
            thread_id=kwargs["thread_id"],
            text=kwargs["text"],
            user_id=kwargs.get("user_id"),
            selected_model=kwargs.get("selected_model"),
            input_type=kwargs.get("input_type"),
            web_search=bool(kwargs.get("web_search", False)),
            deep_research=bool(kwargs.get("deep_research", False)),
            file_context=kwargs.get("file_context") or "",
            route_override=kwargs.get("route_override"),
        )
        result = await self.chat_service.post_message(context)
        metadata = result.metadata.data if hasattr(result.metadata, "data") else {}
        return {"reply": result.reply, "thread_id": result.thread_id, "file_url": result.file_url, "metadata": metadata}
