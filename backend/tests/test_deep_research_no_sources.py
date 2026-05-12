import importlib

import pytest


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str):
        self.choices = [_FakeChoice(content)]


@pytest.mark.asyncio
async def test_deep_research_fast_fallback_when_no_sources(monkeypatch):
    dr = importlib.import_module("service.services.agents.domain.tools.deep_research")

    async def fake_create_chat_completion(messages, model, temperature, max_tokens):
        # Только шаг планирования
        return _FakeResponse('["тестовый запрос"]')

    async def fake_web_search(query: str, num_results: int = 5):
        return []

    monkeypatch.setattr(dr, "create_chat_completion", fake_create_chat_completion)
    monkeypatch.setattr(dr, "web_search", fake_web_search)

    chunks = [chunk async for chunk in dr.deep_research("тема", "fake-model")]
    text = "".join(chunks)

    assert "Всего найдено:** 0 источников" in text
    assert "Внешние источники по теме сейчас недоступны" in text
    assert "### Источники" in text
