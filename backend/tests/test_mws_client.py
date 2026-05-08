import types

import pytest

from service.services.agents.client import mws_client


class _FakeModel:
    def __init__(self, model_id: str):
        self.id = model_id


class _FakeModelsAPI:
    def __init__(self, data):
        self._data = data
        self.calls = 0

    async def list(self):
        self.calls += 1
        return types.SimpleNamespace(data=self._data)


class _FakeClient:
    def __init__(self, data):
        self.models = _FakeModelsAPI(data)


class _BrokenModelsAPI:
    async def list(self):
        raise RuntimeError("upstream unavailable")


class _BrokenClient:
    def __init__(self):
        self.models = _BrokenModelsAPI()


@pytest.mark.asyncio
async def test_list_available_models_cached_between_calls():
    mws_client.clear_models_cache()

    fake_client = _FakeClient(
        [
            _FakeModel("gpt-4o"),
            _FakeModel("gpt-4o-mini"),
            _FakeModel("gpt-4o"),
            _FakeModel(""),
        ]
    )

    first = await mws_client.list_available_models(client=fake_client, force_refresh=True)
    second = await mws_client.list_available_models(client=fake_client)

    assert first == ["gpt-4o", "gpt-4o-mini"]
    assert second == ["gpt-4o", "gpt-4o-mini"]
    assert fake_client.models.calls == 1


@pytest.mark.asyncio
async def test_list_available_models_accepts_dict_items():
    mws_client.clear_models_cache()

    fake_client = _FakeClient(
        [
            {"id": "mws-gpt-alpha"},
            {"id": "kodify-2.0"},
            {"id": "kodify-2.0"},
            {"other": "ignored"},
        ]
    )

    data = await mws_client.list_available_models(client=fake_client, force_refresh=True)
    assert data == ["kodify-2.0", "mws-gpt-alpha"]


@pytest.mark.asyncio
async def test_list_available_models_returns_stale_cache_on_error():
    mws_client.clear_models_cache()

    seed_client = _FakeClient([_FakeModel("gpt-4.1"), _FakeModel("gpt-4.1-mini")])
    seeded = await mws_client.list_available_models(client=seed_client, force_refresh=True)

    broken_client = _BrokenClient()
    fallback = await mws_client.list_available_models(client=broken_client, force_refresh=True)

    assert seeded == ["gpt-4.1", "gpt-4.1-mini"]
    assert fallback == seeded


def test_resolve_mws_base_url_adds_v1_suffix(monkeypatch):
    monkeypatch.setattr(mws_client.config.agents, "mws_base_url", "https://api.gpt.mws.ru")
    monkeypatch.setattr(mws_client.config.agents, "openai_base_url", "")
    assert mws_client._resolve_mws_base_url() == "https://api.gpt.mws.ru/v1"


def test_resolve_mws_base_url_keeps_v1_suffix(monkeypatch):
    monkeypatch.setattr(mws_client.config.agents, "mws_base_url", "https://api.gpt.mws.ru/v1")
    monkeypatch.setattr(mws_client.config.agents, "openai_base_url", "")
    assert mws_client._resolve_mws_base_url() == "https://api.gpt.mws.ru/v1"
