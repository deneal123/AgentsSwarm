import os

import pytest

from orchestrator.services.openai_client import build_openai_client


@pytest.mark.asyncio
async def test_builds_openai_client(monkeypatch):
    monkeypatch.setenv("AGENTS_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    client = build_openai_client()
    assert client.api_key == "test-key"
    assert str(client.base_url).startswith("https://api.openai.com")


@pytest.mark.asyncio
async def test_builds_vllm_client(monkeypatch):
    monkeypatch.setenv("AGENTS_PROVIDER", "vllm")
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.local/v1")
    monkeypatch.setenv("VLLM_API_KEY", "token")
    client = build_openai_client()
    assert str(client.base_url).startswith("http://vllm.local")
    assert client.api_key == "token"


@pytest.mark.asyncio
async def test_missing_env_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AGENTS_PROVIDER", "openai")
    with pytest.raises(RuntimeError):
        build_openai_client()

    monkeypatch.setenv("AGENTS_PROVIDER", "vllm")
    monkeypatch.delenv("VLLM_BASE_URL", raising=False)
    with pytest.raises(RuntimeError):
        build_openai_client()
