import logging

from service.services.chat_contracts import ChatReplyResult
from service.services.process_chat_message_handler import (
    ProcessChatMessageCommand,
    ProcessChatMessageFlags,
    ProcessChatMessageHandler,
    ProcessChatMessageModelSettings,
)

logger = logging.getLogger(__name__)


class ChatJobOrchestrator:
    def __init__(self, handler: ProcessChatMessageHandler) -> None:
        self.handler = handler

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
        command = ProcessChatMessageCommand(
            thread_id=thread_id,
            user_id=user_id,
            text=text,
            flags=ProcessChatMessageFlags(
                web_search=web_search,
                deep_research=deep_research,
                route_override=route_override,
                input_type=input_type,
            ),
            model_settings=ProcessChatMessageModelSettings(selected_model=selected_model),
            file_context=file_context,
            session_data={"session_id": thread_id},
        )
        return await self.handler.dispatch_and_wait(command=command, timeout_sec=30.0)
