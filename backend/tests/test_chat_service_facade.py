import pytest

from service.chat.domain.chat_contracts import (
    ChatProcessingMetadata,
    ChatReplyResult,
    ChatRequestContext,
    ChatRouteDecision,
)
from service.chat.domain.chat_exceptions import JobExecutionError
from service.chat.domain.chat_service import ChatService


@pytest.mark.asyncio
async def test_post_message_uses_orchestrator_and_persists(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ChatService()

    async def _resolve_route(**kwargs):
        return ChatRouteDecision(selected_model="m1", routing_metadata={"tool": "none"})

    async def _execute_job(**kwargs):
        return ChatReplyResult(reply="ok", thread_id="t1", metadata=ChatProcessingMetadata(data={"source": "job"}))

    captured = {"persist": False}

    async def _persist(thread_id, user_text, agent_reply, user_id):
        captured["persist"] = (thread_id, user_text, agent_reply, user_id)

    monkeypatch.setattr(service.routing_service, "resolve_route", _resolve_route)
    monkeypatch.setattr(service.job_orchestrator, "execute", _execute_job)
    monkeypatch.setattr(service.persistence_service, "persist_messages", _persist)

    result = await service.post_message(ChatRequestContext(thread_id="t1", text="hello", user_id=1))

    assert isinstance(result, ChatReplyResult)
    assert result.reply == "ok"
    assert result.metadata.data["source"] == "job"
    assert result.metadata.data["model_routing"] == {"tool": "none"}
    assert captured["persist"] == ("t1", "hello", "ok", 1)


@pytest.mark.asyncio
async def test_post_message_fallback_adds_error_code(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ChatService()

    async def _resolve_route(**kwargs):
        return ChatRouteDecision(selected_model="m1")

    async def _execute_job(**kwargs):
        raise JobExecutionError("boom")

    async def _fallback(**kwargs):
        return ChatReplyResult(reply="fallback", thread_id="t1", metadata=ChatProcessingMetadata(data={}))

    async def _persist(*args, **kwargs):
        return None

    monkeypatch.setattr(service.routing_service, "resolve_route", _resolve_route)
    monkeypatch.setattr(service.job_orchestrator, "execute", _execute_job)
    monkeypatch.setattr(service.fallback_service, "execute", _fallback)
    monkeypatch.setattr(service.persistence_service, "persist_messages", _persist)

    result = await service.post_message(ChatRequestContext(thread_id="t1", text="hello", user_id=1))

    assert result.reply == "fallback"
    assert result.metadata.data["error_code"] == "job_execution_failed"
