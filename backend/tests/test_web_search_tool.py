import importlib

import pytest


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeClient:
    def __init__(self, responses):
        self._responses = responses

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, headers=None):
        if "html.duckduckgo.com" in url:
            return self._responses["html"]
        if "duckduckgo.com/html" in url:
            return self._responses.get("html2", self._responses["html"])
        if "lite.duckduckgo.com" in url:
            return self._responses["lite"]
        if "bing.com/search" in url:
            return self._responses["bing"]
        if "search.brave.com/search" in url:
            return self._responses["brave"]
        if "yandex.ru/search" in url:
            return self._responses["yandex"]
        return self._responses["lite"]


@pytest.mark.asyncio
async def test_web_search_parses_duckduckgo_result_blocks(monkeypatch):
    ws = importlib.import_module("service.agents.tools.web_search")

    html_payload = """
    <html><body>
      <div class="result">
        <h2><a class="result__a" href="https://example.com/a1">Заголовок A1</a></h2>
        <div class="result__snippet">Сниппет A1</div>
      </div>
      <div class="result__body">
        <a class="result__a" href="https://example.com/a2">Заголовок A2</a>
        <span class="result__snippet">Сниппет A2</span>
      </div>
    </body></html>
    """

    lite_payload = "<html><body></body></html>"

    fake_responses = {
        "html": _FakeResponse(html_payload),
        "lite": _FakeResponse(lite_payload),
    }

    monkeypatch.setattr(
        ws.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _FakeClient(fake_responses),
    )

    results = await ws.web_search("test query", num_results=5)

    assert len(results) == 2
    assert results[0]["url"] == "https://example.com/a1"
    assert "Сниппет A1" in results[0]["snippet"]
    assert results[1]["url"] == "https://example.com/a2"


@pytest.mark.asyncio
async def test_web_search_uses_bing_fallback_when_duckduckgo_empty(monkeypatch):
    ws = importlib.import_module("service.agents.tools.web_search")

    empty_html = "<html><body><a href='https://duckduckgo.com/'>DuckDuckGo</a></body></html>"
    # u=a1 + base64("https://example.org/news")
    bing_html = """
    <html><body>
      <li class="b_algo">
        <h2><a href="/ck/a?u=a1aHR0cHM6Ly9leGFtcGxlLm9yZy9uZXdz">Example News</a></h2>
        <div class="b_caption"><p>Актуальные данные и факты.</p></div>
      </li>
    </body></html>
    """

    fake_responses = {
        "html": _FakeResponse(empty_html),
        "html2": _FakeResponse(empty_html),
        "lite": _FakeResponse(empty_html),
        "bing": _FakeResponse(bing_html),
    }

    monkeypatch.setattr(
        ws.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _FakeClient(fake_responses),
    )

    results = await ws.web_search("bing fallback query", num_results=5)

    assert len(results) == 1
    assert results[0]["url"] == "https://example.org/news"
    assert "Актуальные данные" in results[0]["snippet"]


@pytest.mark.asyncio
async def test_web_search_uses_yandex_fallback_when_others_empty(monkeypatch):
    ws = importlib.import_module("service.agents.tools.web_search")

    empty_html = "<html><body><div>no results</div></body></html>"
    yandex_html = """
    <html><body>
      <li class="serp-item">
        <h2><a href="https://example.net/cats">Сиамские кошки: обзор</a></h2>
        <div class="organic__text">Подробный материал по теме.</div>
      </li>
    </body></html>
    """

    fake_responses = {
        "html": _FakeResponse(empty_html),
        "html2": _FakeResponse(empty_html),
        "lite": _FakeResponse(empty_html),
        "bing": _FakeResponse(empty_html),
        "brave": _FakeResponse(empty_html),
        "yandex": _FakeResponse(yandex_html),
    }

    monkeypatch.setattr(
        ws.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _FakeClient(fake_responses),
    )

    results = await ws.web_search("yandex fallback query", num_results=5)

    assert len(results) == 1
    assert results[0]["url"] == "https://example.net/cats"
    assert "Подробный материал" in results[0]["snippet"]


@pytest.mark.asyncio
async def test_web_search_uses_brave_fallback_when_duck_bing_lite_empty(monkeypatch):
    ws = importlib.import_module("service.agents.tools.web_search")

    empty_html = "<html><body><div>no results</div></body></html>"
    brave_html = """
    <html><body>
      <div class="snippet" data-type="web">
        <a href="https://example.dev/openai-models">
          <div class="title search-snippet-title">OpenAI Models Overview</div>
        </a>
        <div class="generic-snippet"><div class="content">Latest updates and model lineup.</div></div>
      </div>
    </body></html>
    """

    fake_responses = {
        "html": _FakeResponse(empty_html),
        "html2": _FakeResponse(empty_html),
        "lite": _FakeResponse(empty_html),
        "bing": _FakeResponse(empty_html),
        "brave": _FakeResponse(brave_html),
        "yandex": _FakeResponse(empty_html),
    }

    monkeypatch.setattr(
        ws.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _FakeClient(fake_responses),
    )

    results = await ws.web_search("brave fallback query", num_results=5)

    assert len(results) == 1
    assert results[0]["url"] == "https://example.dev/openai-models"
    assert "Latest updates" in results[0]["snippet"]
