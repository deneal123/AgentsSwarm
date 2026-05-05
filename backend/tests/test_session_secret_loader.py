import os
import pytest

from service.agents.sessions import create_session
from service.infrastructure.secrets import secret_loader


@pytest.mark.asyncio
async def test_create_session_uses_secret_loader(monkeypatch):
    # ensure settings has no explicit key
    monkeypatch.setattr(secret_loader, "get_encryption_key", lambda *a, **k: "secret-key-base64")

    # choose redis backend by making redis enabled in config
    from service.settings import config
    config.sessions.encryption_key = None
    config.redis.enabled = False

    # provide a fake redis client via container.get
    class FakeRedis:
        pass

    fake = FakeRedis()
    import service.container as di

    monkeypatch.setattr(di, "get", lambda name: fake)

    s = create_session("s1", backend="redis", max_items=2)
    assert s is not None
    # secret loader returns a value, so instance should have _encryption_key set
    assert getattr(s, "_encryption_key", None) in (b"secret-key-base64", "secret-key-base64")
