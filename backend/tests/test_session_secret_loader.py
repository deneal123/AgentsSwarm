import pytest

from service.services.agents.infrastructure.sessions import create_session
from service.infrastructure.secrets import secret_loader


@pytest.mark.asyncio
async def test_create_session_uses_secret_loader(monkeypatch):
    monkeypatch.setattr(secret_loader, "get_encryption_key", lambda *a, **k: "secret-key-base64")

    from service.settings import config
    config.sessions.encryption_key = None
    config.redis.enabled = False

    class FakeRedis:
        pass

    class FakeInfra:
        redis_client = FakeRedis()

    class FakeContainer:
        infra = FakeInfra()

    monkeypatch.setattr(
        "service.composition.state.get_current_container",
        lambda: FakeContainer(),
    )

    s = create_session("s1", backend="redis", max_items=2)
    assert s is not None
    assert getattr(s, "_encryption_key", None) in (b"secret-key-base64", "secret-key-base64")
