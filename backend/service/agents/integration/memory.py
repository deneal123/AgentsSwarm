"""Mem0-backed memory integration for agent layer."""

from __future__ import annotations

import asyncio
import inspect
import os
from typing import Any

from service.agents.integration.base import BaseMemoryIntegration

try:
    from mem0 import MemoryClient as _Mem0MemoryClient  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency
    try:
        from mem0ai import MemoryClient as _Mem0MemoryClient  # type: ignore[import-not-found]
    except Exception:  # pragma: no cover - optional dependency
        _Mem0MemoryClient = None


class Mem0MemoryIntegration(BaseMemoryIntegration):
    """Memory provider based on mem0ai SDK.

    Notes:
    - Uses best-effort mode: any provider error is logged and swallowed.
    - Methods stay non-blocking for async call-sites via ``asyncio.to_thread``.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        default_top_k: int = 5,
        client: Any | None = None,
    ) -> None:
        super().__init__(name="mem0")
        self._api_key = self._resolve_api_key(api_key)
        self._app_id = (
            os.getenv("MEM0_APP_ID")
            or os.getenv("MEM0__APP_ID")
            or os.getenv("AGENTS__MEM0_APP_ID")
            or "gpthub"
        ).strip()
        self._default_top_k = default_top_k
        self._client = client

    @staticmethod
    def _resolve_api_key(explicit_api_key: str | None) -> str:
        return (
            explicit_api_key
            or os.getenv("MEM0_API_KEY")
            or os.getenv("MEM0AI_API_KEY")
            or os.getenv("MEM0__API_KEY")
            or os.getenv("AGENTS__MEM0_API_KEY")
            or os.getenv("SERVICE__MEM0_API_KEY")
            or ""
        ).strip()

    @property
    def available(self) -> bool:
        if self._client is not None:
            return True
        if _Mem0MemoryClient is None:
            return False
        # For cloud Mem0 this key is typically required.
        return bool(self._api_key)

    async def _ensure_client(self) -> Any | None:
        if self._client is not None:
            return self._client
        if not self.available:
            return None

        if _Mem0MemoryClient is None:
            return None

        try:
            # Try explicit key first (covers newer SDK variants).
            self._client = _Mem0MemoryClient(api_key=self._api_key)
        except TypeError:
            # Fallback to env-driven initialization.
            if self._api_key:
                os.environ.setdefault("MEM0_API_KEY", self._api_key)
            self._client = _Mem0MemoryClient()
        return self._client

    async def get_memory_context(self, *, user_id: str, top_k: int = 5) -> str:
        if not user_id:
            return ""

        started = self._log_operation_start("mem0.get_memory_context", user_id=user_id, top_k=top_k)
        client = await self._ensure_client()
        if client is None:
            return ""

        try:
            query = "user preferences profile facts goals constraints recent context"
            payload = await asyncio.to_thread(self._search_memories_sync, client, query, user_id, top_k)
            memories = self._extract_memory_texts(payload)
            if not memories:
                self._log_operation_success("mem0.get_memory_context", started, memories=0)
                return ""

            formatted = "## Контекст из памяти пользователя:\n" + "\n".join(f"- {item}" for item in memories)
            self._log_operation_success("mem0.get_memory_context", started, memories=len(memories))
            return formatted
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            self._log_operation_failure("mem0.get_memory_context", started, exc)
            return ""

    async def save_messages(
        self,
        *,
        user_id: str,
        messages: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not user_id or not messages:
            return

        started = self._log_operation_start(
            "mem0.save_messages",
            user_id=user_id,
            messages=len(messages),
            has_metadata=bool(metadata),
        )
        client = await self._ensure_client()
        if client is None:
            return

        try:
            normalized_messages = [
                {
                    "role": str(item.get("role") or "user"),
                    "content": str(item.get("content") or ""),
                }
                for item in messages
                if str(item.get("content") or "").strip()
            ]
            if not normalized_messages:
                return

            await asyncio.to_thread(
                self._add_memories_sync,
                client,
                normalized_messages,
                user_id,
                metadata,
            )
            self._log_operation_success("mem0.save_messages", started, saved=len(normalized_messages))
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            self._log_operation_failure("mem0.save_messages", started, exc)

    async def list_facts(
        self,
        *,
        user_id: str,
        query: str | None = None,
        top_k: int = 50,
    ) -> list[dict[str, Any]]:
        if not user_id:
            return []

        started = self._log_operation_start(
            "mem0.list_facts",
            user_id=user_id,
            query=bool(query),
            top_k=top_k,
        )
        client = await self._ensure_client()
        if client is None:
            return []

        try:
            if query and query.strip():
                payload = await asyncio.to_thread(
                    self._search_memories_sync,
                    client,
                    query.strip(),
                    user_id,
                    top_k,
                )
            else:
                payload = await asyncio.to_thread(self._get_all_memories_sync, client, user_id, top_k)

            facts = self._extract_memory_items(payload)
            self._log_operation_success("mem0.list_facts", started, facts=len(facts))
            return facts
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            self._log_operation_failure("mem0.list_facts", started, exc)
            return []

    async def add_fact(
        self,
        *,
        user_id: str,
        fact_type: str,
        fact_key: str,
        fact_value: str,
    ) -> dict[str, Any]:
        if not user_id or not fact_key.strip() or not fact_value.strip():
            return {}

        started = self._log_operation_start("mem0.add_fact", user_id=user_id, fact_type=fact_type)
        client = await self._ensure_client()
        if client is None:
            return {}

        metadata = {
            "fact_type": fact_type.strip() or "general",
            "fact_key": fact_key.strip(),
            "fact_value": fact_value.strip(),
            "source": "manual",
        }
        messages = [{"role": "user", "content": f"{fact_key.strip()}: {fact_value.strip()}"}]

        try:
            payload = await asyncio.to_thread(self._add_memories_sync, client, messages, user_id, metadata)
            created = payload if isinstance(payload, dict) else {}
            self._log_operation_success("mem0.add_fact", started)
            return created
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            self._log_operation_failure("mem0.add_fact", started, exc)
            return {}

    async def delete_fact(self, *, user_id: str, fact_id: str) -> bool:
        if not user_id or not fact_id:
            return False

        started = self._log_operation_start("mem0.delete_fact", user_id=user_id, fact_id=fact_id)
        client = await self._ensure_client()
        if client is None:
            return False

        try:
            await asyncio.to_thread(self._delete_memory_sync, client, fact_id)
            self._log_operation_success("mem0.delete_fact", started)
            return True
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            self._log_operation_failure("mem0.delete_fact", started, exc)
            return False

    def _search_memories_sync(self, client: Any, query: str, user_id: str, top_k: int) -> Any:
        """Call mem0 search with cross-version fallback for signatures."""
        top_k = top_k or self._default_top_k
        filters_with_app = {"AND": [{"user_id": user_id}, {"app_id": self._app_id}]}
        filters_user_only = {"user_id": user_id}
        candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = [
            ((query,), {"filters": filters_with_app, "top_k": top_k}),
            ((query,), {"filters": filters_user_only, "top_k": top_k, "app_id": self._app_id}),
            ((query,), {"filters": filters_user_only, "top_k": top_k}),
            ((), {"query": query, "user_id": user_id, "top_k": top_k, "app_id": self._app_id}),
            ((query,), {"user_id": user_id, "top_k": top_k, "app_id": self._app_id}),
            ((), {"query": query, "user_id": user_id, "top_k": top_k}),
            ((query,), {"user_id": user_id, "top_k": top_k}),
            ((query,), {"user_id": user_id}),
        ]

        method = client.search
        last_exc: Exception | None = None
        for args, kwargs in candidates:
            try:
                return method(*args, **kwargs)
            except TypeError as exc:
                last_exc = exc
                continue

        if last_exc:
            raise last_exc
        return method(query=query, user_id=user_id)

    def _add_memories_sync(
        self,
        client: Any,
        messages: list[dict[str, Any]],
        user_id: str,
        metadata: dict[str, Any] | None,
    ) -> Any:
        """Call mem0 add with cross-version fallback for signatures."""
        method = client.add
        candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = [
            (
                (),
                {
                    "messages": messages,
                    "user_id": user_id,
                    "metadata": metadata,
                    "app_id": self._app_id,
                    "async_mode": False,
                },
            ),
            (
                (messages,),
                {
                    "user_id": user_id,
                    "metadata": metadata,
                    "app_id": self._app_id,
                    "async_mode": False,
                },
            ),
            ((messages,), {"user_id": user_id, "metadata": metadata}),
            ((messages,), {"user_id": user_id}),
        ]

        last_exc: Exception | None = None
        for args, kwargs in candidates:
            # Remove unsupported kwargs proactively when possible.
            safe_kwargs = self._filter_supported_kwargs(method, kwargs)
            try:
                return method(*args, **safe_kwargs)
            except TypeError as exc:
                last_exc = exc
                continue

        if last_exc:
            raise last_exc
        return method(messages)

    def _get_all_memories_sync(self, client: Any, user_id: str, top_k: int) -> Any:
        method = client.get_all
        filters_with_app = {"AND": [{"user_id": user_id}, {"app_id": self._app_id}]}
        filters_user_only = {"user_id": user_id}
        candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = [
            ((), {"filters": filters_with_app, "top_k": top_k}),
            ((), {"filters": filters_user_only, "top_k": top_k, "app_id": self._app_id}),
            ((), {"filters": filters_user_only, "top_k": top_k}),
            ((), {"user_id": user_id, "top_k": top_k, "app_id": self._app_id}),
            ((), {"user_id": user_id, "top_k": top_k}),
            ((), {"user_id": user_id}),
        ]

        last_exc: Exception | None = None
        for args, kwargs in candidates:
            safe_kwargs = self._filter_supported_kwargs(method, kwargs)
            try:
                return method(*args, **safe_kwargs)
            except TypeError as exc:
                last_exc = exc
                continue

        if last_exc:
            raise last_exc
        return method()

    @staticmethod
    def _delete_memory_sync(client: Any, memory_id: str) -> Any:
        return client.delete(memory_id)

    @staticmethod
    def _filter_supported_kwargs(method: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
        try:
            sig = inspect.signature(method)
        except Exception:
            return kwargs

        supported = set(sig.parameters.keys())
        accepts_var_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        if accepts_var_kwargs:
            return kwargs

        return {k: v for k, v in kwargs.items() if k in supported and v is not None}

    @staticmethod
    def _extract_memory_texts(payload: Any) -> list[str]:
        if payload is None:
            return []

        if isinstance(payload, dict):
            results = payload.get("results")
            if isinstance(results, list):
                return Mem0MemoryIntegration._extract_memory_texts(results)
            return []

        texts: list[str] = []
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, str) and item.strip():
                    texts.append(item.strip())
                    continue
                if isinstance(item, dict):
                    candidate = item.get("memory") or item.get("text") or item.get("content")
                    if isinstance(candidate, str) and candidate.strip():
                        texts.append(candidate.strip())

        # Keep prompt concise.
        return texts[:10]

    @staticmethod
    def _extract_memory_items(payload: Any) -> list[dict[str, Any]]:
        if payload is None:
            return []

        if isinstance(payload, dict):
            results = payload.get("results")
            if isinstance(results, list):
                return Mem0MemoryIntegration._extract_memory_items(results)
            if isinstance(payload.get("memory"), str):
                return [payload]
            return []

        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        return []
