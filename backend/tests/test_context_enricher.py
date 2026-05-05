import pytest

from service.agents.pipeline.context_enricher import (
    build_effective_input,
    load_session_history_context,
)


class _FakeSession:
    def __init__(self, items):
        self.items = items
        self.last_limit = None

    async def get_items(self, limit=None):
        self.last_limit = limit
        if limit is None:
            return list(self.items)
        return list(self.items)[-limit:]


@pytest.mark.asyncio
async def test_load_session_history_context_uses_limit_and_formats_roles(caplog):
    session = _FakeSession(
        [
            {"role": "user", "content": "Привет"},
            {"role": "assistant", "content": "Здравствуйте"},
            {"role": "user", "content": "Сделай план"},
        ]
    )

    context = await load_session_history_context(
        session,
        caplog,
        limit_messages=2,
        max_chars=500,
    )

    assert session.last_limit == 2
    assert "История чата" in context
    assert "Ассистент: Здравствуйте" in context
    assert "Пользователь: Сделай план" in context
    assert "Пользователь: Привет" not in context


def test_build_effective_input_enforces_max_context_chars():
    user_input = "Сформируй ответ"
    memory_context = "M" * 300
    history_context = "H" * 300
    file_context = "F" * 300

    result = build_effective_input(
        user_input,
        memory_context=memory_context,
        chat_history_context=history_context,
        file_context=file_context,
        max_context_chars=220,
    )

    assert result.startswith(user_input)
    assert len(result) <= 220


def test_build_effective_input_without_extra_context_returns_input():
    result = build_effective_input("hello", max_context_chars=10)
    assert result == "hello"
