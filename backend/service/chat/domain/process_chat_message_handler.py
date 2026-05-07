from dataclasses import dataclass, field
from typing import Any

from service.ports import ChatCommandPort, JobOrchestrationPort, JobQueuePort

from uuid import UUID

from service.chat.domain.chat_contracts import ChatProcessingMetadata, ChatReplyResult, build_provider_unavailable_reply
from service.chat.domain.chat_exceptions import (
    JobCreationError,
    JobEnqueueError,
    JobExecutionError,
    JobServiceUnavailableError,
)


@dataclass(slots=True)
class ProcessChatMessageFlags:
    web_search: bool = False
    deep_research: bool = False
    route_override: str | None = None
    input_type: str | None = None


@dataclass(slots=True)
class ProcessChatMessageModelSettings:
    selected_model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(slots=True)
class ProcessChatMessageCommand:
    thread_id: str
    user_id: str | int | None
    text: str
    flags: ProcessChatMessageFlags = field(default_factory=ProcessChatMessageFlags)
    model_settings: ProcessChatMessageModelSettings = field(default_factory=ProcessChatMessageModelSettings)
    file_context: str = ""
    session_data: dict[str, Any] | None = None


class ProcessChatMessageHandler(ChatCommandPort):
    def __init__(self, job_service: JobOrchestrationPort, job_queue: JobQueuePort) -> None:
        self.job_service = job_service
        self.job_queue = job_queue

    @staticmethod
    def normalize_user_uuid(user_id: str | int | None) -> UUID | None:
        if user_id is None:
            return None
        normalized = str(user_id).strip()
        if not normalized or normalized.lower() in {"none", "null"}:
            return None
        try:
            return UUID(normalized)
        except Exception:
            return None

    @staticmethod
    def normalize_result_payload(result: dict[str, Any], *, thread_id: str, selected_model: str | None) -> ChatReplyResult:
        reply = str(result.get("reply") or "")
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        if selected_model and "selected_model" not in metadata:
            metadata = {**metadata, "selected_model": selected_model}
        if not reply.strip():
            provider_error = metadata.get("provider_error")
            reply = build_provider_unavailable_reply(provider_error)
            metadata = {**metadata, "provider_unavailable": True}
        return ChatReplyResult(
            reply=reply,
            thread_id=thread_id,
            file_url=result.get("file_url"),
            metadata=ChatProcessingMetadata(data=metadata),
        )

    async def dispatch_and_wait(self, command: ProcessChatMessageCommand, *, timeout_sec: float = 30.0) -> ChatReplyResult:
        if self.job_service is None:
            raise JobServiceUnavailableError("JobService unavailable")

        try:
            job_response = await self.job_service.create_chat_job(
                user_id=self.normalize_user_uuid(command.user_id),
                thread_id=command.thread_id,
                text=command.text,
            )
        except Exception as exc:
            raise JobCreationError("Failed to create chat job") from exc

        try:
            task = self.job_queue.enqueue_process_agent_message(
                job_id=str(job_response.job_id),
                thread_id=command.thread_id,
                text=command.text,
                user_id=str(command.user_id) if command.user_id else None,
                session_data=command.session_data or {"session_id": command.thread_id},
                selected_model=command.model_settings.selected_model,
                route_override=command.flags.route_override,
                input_type=command.flags.input_type,
                web_search=command.flags.web_search,
                deep_research=command.flags.deep_research,
                file_context=command.file_context,
            )
        except Exception as exc:
            raise JobEnqueueError("Failed to enqueue chat task") from exc

        try:
            result = task.get(timeout=timeout_sec)
        except Exception as exc:
            raise JobExecutionError("Failed waiting for chat task result") from exc

        if result.get("status") != "success":
            raise JobExecutionError(str(result.get("error") or "Task failed"))

        return self.normalize_result_payload(
            result,
            thread_id=command.thread_id,
            selected_model=command.model_settings.selected_model,
        )

    async def process_for_worker(self, job_id: str, command: ProcessChatMessageCommand) -> dict[str, Any]:
        return await self.job_queue.process_agent_message(
            job_id=job_id,
            thread_id=command.thread_id,
            text=command.text,
            user_id=str(command.user_id) if command.user_id is not None else None,
            session_data=command.session_data,
            selected_model=command.model_settings.selected_model,
            route_override=command.flags.route_override,
            input_type=command.flags.input_type,
            web_search=command.flags.web_search,
            deep_research=command.flags.deep_research,
            file_context=command.file_context,
        )
