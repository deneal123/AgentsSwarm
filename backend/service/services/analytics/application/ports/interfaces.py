from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MemoryIntegrationPort(Protocol):
    async def get_memory_context(self, *, user_id: str, top_k: int = 5) -> str: ...
    async def save_messages(
        self,
        *,
        user_id: str,
        messages: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> None: ...
    async def list_facts(
        self, *, user_id: str, query: str | None = None, top_k: int = 50
    ) -> list[dict[str, Any]]: ...
    async def add_fact(
        self, *, user_id: str, fact_type: str, fact_key: str, fact_value: str
    ) -> dict[str, Any]: ...
    async def delete_fact(self, *, user_id: str, fact_id: str) -> bool: ...
