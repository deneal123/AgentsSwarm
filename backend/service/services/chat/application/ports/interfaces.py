from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ChatCommandPort(Protocol):
    async def dispatch_and_wait(self, command: Any, *, timeout_sec: float = 30.0) -> Any: ...
