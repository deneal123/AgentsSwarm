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
async def test_deep_research_uses_snippet_when_parse_url_has_no_content(monkeypatch):
    dr = importlib.import_module("service.services.agents.domain.tools.deep_research")

    async def fake_create_chat_completion(messages, model, temperature, max_tokens):
        system_content = str(messages[0].get("content", ""))
        if "ТОЛЬКО JSON" in system_content:
            return _FakeResponse('["тестовый запрос"]')
        return _FakeResponse("Итоговый отчёт")

    async def fake_web_search(query: str, num_results: int = 3):
        return [
            {
                "title": "Тестовый источник",
                "url": "https://example.com/article",
                "snippet": "Краткий полезный сниппет из поиска",
            }
        ]

    async def fake_parse_url(url: str, max_chars: int = 3000):
        return {"url": url, "title": "", "content": "", "error": "403"}

    monkeypatch.setattr(dr, "create_chat_completion", fake_create_chat_completion)
    monkeypatch.setattr(dr, "web_search", fake_web_search)
    monkeypatch.setattr(dr, "parse_url", fake_parse_url)

    chunks = [chunk async for chunk in dr.deep_research("тема", "fake-model")]
    text = "".join(chunks)

    assert "Проанализировано:** 1 источников" in text
    assert "### Источники" in text
    assert "https://example.com/article" in text
