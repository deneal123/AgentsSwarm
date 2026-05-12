import pytest

from service.services.chat.domain.chat_contracts import (
    ChatProcessingMetadata,
    ChatReplyResult,
    ChatRequestContext,
    ChatRouteDecision,
)
from service.services.chat.domain.chat_exceptions import JobExecutionError
from service.services.chat.domain.chat_service import ChatService


class _FakeRoutingService:
    async def resolve_route(self, **kwargs):
        return ChatRouteDecision(selected_model="m1", routing_metadata={"tool": "none"})


class _FakeOrchestration:
    async def execute(self, **kwargs):
        return ChatReplyResult(reply="ok", thread_id="t1", metadata=ChatProcessingMetadata(data={"source": "job"}))


class _FakePersistence:
    async def persist_messages(self, thread_id, user_text, agent_reply, user_id):
        pass

    async def create_thread(self, **kwargs):
        return {"thread_id": "t1", "title": None}

    async def get_thread_messages(self, **kwargs):
        return {"thread_id": "t1", "messages": []}

    async def list_threads(self, **kwargs):
        return {"threads": []}

    async def delete_thread(self, thread_id):
        return True


class _FakeFallback:
    async def execute(self, **kwargs):
        return ChatReplyResult(reply="fallback", thread_id="t1", metadata=ChatProcessingMetadata(data={}))


@pytest.mark.asyncio
async def test_post_message_uses_orchestrator_and_persists(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {"persist": False}

    class _Persistence(_FakePersistence):
        async def persist_messages(self, thread_id, user_text, agent_reply, user_id):
            captured["persist"] = (thread_id, user_text, agent_reply, user_id)

    service = ChatService(
        routing_service=_FakeRoutingService(),
        orchestration_service=_FakeOrchestration(),
        persistence_service=_Persistence(),
        fallback_service=_FakeFallback(),
    )

    result = await service.post_message(ChatRequestContext(thread_id="t1", text="hello", user_id=1))

    assert isinstance(result, ChatReplyResult)
    assert result.reply == "ok"
    assert result.metadata.data["source"] == "job"
    assert result.metadata.data["model_routing"] == {"tool": "none"}
    assert captured["persist"] == ("t1", "hello", "ok", 1)


@pytest.mark.asyncio
async def test_post_message_fallback_adds_error_code(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FailingOrchestration:
        async def execute(self, **kwargs):
            raise JobExecutionError("boom")

    service = ChatService(
        routing_service=_FakeRoutingService(),
        orchestration_service=_FailingOrchestration(),
        persistence_service=_FakePersistence(),
        fallback_service=_FakeFallback(),
    )

    result = await service.post_message(ChatRequestContext(thread_id="t1", text="hello", user_id=1))

    assert result.reply == "fallback"
    assert result.metadata.data["error_code"] == "job_execution_failed"
