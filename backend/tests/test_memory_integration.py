import pytest

from service.infrastructure.messaging.tasks import _resolve_memory_user_id
from service.services.agents.infrastructure.integration.base import (
    BaseIntegration,
    BaseMemoryIntegration,
)
from service.services.agents.infrastructure.integration.memory import Mem0MemoryIntegration
from service.services.analytics.application.memory_service import MemoryService


class _FakeMem0Client:
    def __init__(self) -> None:
        self.saved_calls: list[dict] = []

    def search(self, query: str, user_id: str, top_k: int = 5):  # noqa: ANN001
        return {
            "results": [
                {"memory": "Пользователь предпочитает короткие ответы"},
                {"memory": "Работает с FastAPI"},
            ]
        }

    def add(self, messages, user_id: str, metadata=None):  # noqa: ANN001
        self.saved_calls.append(
            {
                "messages": messages,
                "user_id": user_id,
                "metadata": metadata,
            }
        )
        return {"status": "ok"}


class _FakeIntegration(BaseMemoryIntegration):
    def __init__(self) -> None:
        super().__init__(name="fake")
        self.saved: list[dict] = []

    @property
    def available(self) -> bool:
        return True

    async def get_memory_context(self, *, user_id: str, top_k: int = 5) -> str:
        return f"memory-for-{user_id}-k{top_k}"

    async def save_messages(
        self, *, user_id: str, messages: list[dict], metadata: dict | None = None
    ) -> None:
        self.saved.append({"user_id": user_id, "messages": messages, "metadata": metadata})

    async def list_facts(
        self, *, user_id: str, query: str | None = None, top_k: int = 50
    ) -> list[dict]:
        return []

    async def add_fact(
        self, *, user_id: str, fact_type: str, fact_key: str, fact_value: str
    ) -> dict:
        return {}

    async def delete_fact(self, *, user_id: str, fact_id: str) -> bool:
        return False


@pytest.mark.asyncio
async def test_mem0_integration_formats_context_from_results() -> None:
    integration = Mem0MemoryIntegration(client=_FakeMem0Client())

    context = await integration.get_memory_context(user_id="user-1", top_k=3)

    assert "Контекст из памяти пользователя" in context
    assert "Пользователь предпочитает короткие ответы" in context
    assert "Работает с FastAPI" in context


@pytest.mark.asyncio
async def test_mem0_integration_saves_messages() -> None:
    client = _FakeMem0Client()
    integration = Mem0MemoryIntegration(client=client)

    await integration.save_messages(
        user_id="user-2",
        messages=[{"role": "user", "content": "Мне нравятся диаграммы"}],
        metadata={"thread_id": "thread-1"},
    )

    assert len(client.saved_calls) == 1
    assert client.saved_calls[0]["user_id"] == "user-2"
    assert client.saved_calls[0]["messages"][0]["content"] == "Мне нравятся диаграммы"


@pytest.mark.asyncio
async def test_memory_service_delegates_to_integration() -> None:
    integration = _FakeIntegration()
    service = MemoryService(integration=integration)

    context = await service.get_memory_context("user-3", top_k=7)
    await service.extract_and_save_facts(
        user_id="user-3",
        thread_id="thread-2",
        messages=[{"role": "user", "content": "Сохрани этот факт"}],
    )

    assert context == "memory-for-user:user-3-k7"
    assert len(integration.saved) == 1
    assert integration.saved[0]["user_id"] == "user:user-3"
    assert integration.saved[0]["metadata"]["thread_id"] == "thread-2"
    assert integration.saved[0]["metadata"]["source"] == "gpthub-agent"
    assert integration.saved[0]["metadata"]["user_scope"] == "user:user-3"


def test_memory_integration_inherits_from_generic_base() -> None:
    integration = Mem0MemoryIntegration(client=_FakeMem0Client())

    assert isinstance(integration, BaseIntegration)
    assert isinstance(integration, BaseMemoryIntegration)


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDbSession:
    def __init__(self, value):
        self._value = value

    async def execute(self, *_args, **_kwargs):
        return _FakeScalarResult(self._value)


@pytest.mark.asyncio
async def test_resolve_memory_user_id_prefers_explicit_user() -> None:
    db = _FakeDbSession("from-thread")

    resolved = await _resolve_memory_user_id(
        db_session=db, user_id="real-user", thread_id="thread-1"
    )

    assert resolved == "real-user"


@pytest.mark.asyncio
async def test_resolve_memory_user_id_falls_back_to_thread_owner() -> None:
    db = _FakeDbSession("thread-owner-user")

    resolved = await _resolve_memory_user_id(
        db_session=db,
        user_id="00000000-0000-0000-0000-000000000000",
        thread_id="thread-2",
    )

    assert resolved == "thread-owner-user"
