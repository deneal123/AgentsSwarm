from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class JobOrchestrationPort(Protocol):
    async def create_chat_job(self, user_id: Any, thread_id: str, text: str) -> Any:
        ...


@runtime_checkable
class JobHandlePort(Protocol):
    def get(self, timeout: float) -> dict[str, Any]:
        ...


@runtime_checkable
class JobQueuePort(Protocol):
    def enqueue_process_agent_message(self, **kwargs: Any) -> JobHandlePort:
        ...

    def enqueue_agent_message(self, **kwargs: Any) -> str | None:
        ...

    async def process_agent_message(self, **kwargs: Any) -> dict[str, Any]:
        ...

    def get_task_state(self, task_id: str) -> tuple[bool, bool, Any, Any, str]:
        ...

    def cancel_task(self, task_id: str) -> bool:
        ...
