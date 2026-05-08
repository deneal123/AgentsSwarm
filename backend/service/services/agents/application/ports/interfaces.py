from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StreamPort(Protocol):
    async def publish(self, stream: str, payload: dict[str, Any]) -> None:
        ...


@runtime_checkable
class AgentExecutionPort(Protocol):
    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        ...
