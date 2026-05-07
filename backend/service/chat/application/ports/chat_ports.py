from __future__ import annotations

from typing import Protocol

from service.chat.domain.chat_contracts import ChatReplyResult, ChatRequestContext, JobExecutionResult


class ChatMessageProcessorPort(Protocol):
    async def execute(self, context: ChatRequestContext) -> ChatReplyResult: ...


class ChatPersistencePort(Protocol):
    async def create_thread(self, user_id: str | int | None, title: str | None, thread_id: str | None = None) -> dict: ...
    async def persist_messages(self, thread_id: str, user_text: str, assistant_text: str, user_id: str | int | None = None) -> None: ...
    async def get_messages(self, thread_id: str, page: int = 1, per_page: int = 50) -> dict: ...
    async def list_threads(self, user_id: str | int | None = None, page: int = 1, per_page: int = 50) -> dict: ...
    async def delete_thread(self, thread_id: str) -> bool: ...


class ChatStreamingPort(Protocol):
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
    ) -> ChatReplyResult: ...


class ChatOrchestrationPort(Protocol):
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
    ) -> JobExecutionResult: ...
