from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MessageBusPort(Protocol):
    async def push(self, queue: str, payload: str) -> None:
        ...


@runtime_checkable
class StreamPort(Protocol):
    async def publish(self, stream: str, payload: dict[str, Any]) -> None:
        ...


@runtime_checkable
class FileStoragePort(Protocol):
    def build_file_path(self, folder: str, mode: str, file_name: str) -> str:
        ...

    async def upload_file(self, *, file_key: str, file_data: bytes) -> str:
        ...

    async def delete_file(self, *, file_key: str) -> None:
        ...


@runtime_checkable
class ChatCommandPort(Protocol):
    async def dispatch_and_wait(self, command: Any, *, timeout_sec: float = 30.0) -> Any:
        ...


@runtime_checkable
class JobOrchestrationPort(Protocol):
    async def create_chat_job(self, user_id: Any, thread_id: str, text: str) -> Any:
        ...


@runtime_checkable
class AgentExecutionPort(Protocol):
    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        ...

@runtime_checkable
class JobHandlePort(Protocol):
    def get(self, timeout: float) -> dict[str, Any]:
        ...


@runtime_checkable
class JobQueuePort(Protocol):
    def enqueue_process_agent_message(self, **kwargs: Any) -> JobHandlePort:
        ...

    async def process_agent_message(self, **kwargs: Any) -> dict[str, Any]:
        ...

    def enqueue_calendar_generation(self, args: list[Any]) -> str | None:
        ...

    def get_task_state(self, task_id: str) -> tuple[bool, bool, Any, Any, str]:
        ...
