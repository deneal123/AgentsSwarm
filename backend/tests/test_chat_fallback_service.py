import pytest

from service.chat.domain.chat_fallback_service import ChatFallbackService


class _Agent:
    async def handle_message(self, thread_id, text, user_id):
        return {"reply": "agent-reply", "thread_id": thread_id, "metadata": {"x": 1}}


@pytest.mark.asyncio
async def test_execute_basic_path() -> None:
    service = ChatFallbackService(agent=_Agent())

    result = await service.execute(
        thread_id="t1",
        text="hello",
        user_id=1,
        selected_model=None,
        input_type=None,
        web_search=False,
        deep_research=False,
        file_context="",
        route_override=None,
    )

    assert result.reply == "agent-reply"
    assert result.thread_id == "t1"
    assert result.metadata["x"] == 1


@pytest.mark.asyncio
async def test_execute_empty_reply_marks_provider_unavailable() -> None:
    class _EmptyAgent:
        async def handle_message(self, thread_id, text, user_id):
            return {"reply": "", "thread_id": thread_id, "metadata": {"error": "provider down"}}

    service = ChatFallbackService(agent=_EmptyAgent())
    result = await service.execute("t2", "hello", 1, None, None, False, False, "", None)

    assert result.metadata["provider_unavailable"] is True
    assert "provider down" in result.reply
