import json

from fastapi.testclient import TestClient
from service.composition.state import get_app_container, get_optional_redis_client, get_optional_redis_session_store
from service.settings import config


class _FakeSessionStore:
    async def get_session_by_token(self, token):
        if token == "good-token":
            return {"id": "s1", "user_id": "u1"}
        return None


class _FakeChatService:
    pass


class _FakeChatAppService:
    class _Services:
        chat_service = _FakeChatService()
    services = _Services()


class _FakeServices:
    job_service = None
    file_saver_service = None
    chat_application_service = _FakeChatAppService()


class _FakeContainer:
    services = _FakeServices()


def _make_fake_container():
    return _FakeContainer()


def test_replay_with_last_id(monkeypatch):
    monkeypatch.setattr(config.auth, "auth_mode", "dev")
    monkeypatch.setattr(config.auth, "ws_auth_allowlist_dev", ["query_token", "anon_token"])
    monkeypatch.setattr(config.auth, "enable_legacy_ws_token_auth", True)
    from service.main import app

    class FakeRedis:
        async def xgroup_create(self, stream, group, id="0", mkstream=False):
            return True

        async def xrange(self, stream, start, end, count=100):
            return [("1-0", {"data": json.dumps({"event": "replay", "seq": 1})})]

        async def xpending(self, stream, group):
            return {"count": 0}

        async def xread(self, streams=None, count=10, timeout=0):
            return []

    app.dependency_overrides[get_optional_redis_session_store] = lambda: _FakeSessionStore()
    app.dependency_overrides[get_optional_redis_client] = lambda: FakeRedis()
    app.dependency_overrides[get_app_container] = _make_fake_container

    try:
        client = TestClient(app)
        with client.websocket_connect("/api/chats/thread-replay/ws?token=good-token&last_id=0-0") as ws:
            msg = ws.receive_json()
            assert msg.get("type") == "replay"
            assert msg.get("data", {}).get("event") == "replay"
    finally:
        app.dependency_overrides.pop(get_optional_redis_session_store, None)
        app.dependency_overrides.pop(get_optional_redis_client, None)
        app.dependency_overrides.pop(get_app_container, None)


def test_claim_pending_on_reconnect(monkeypatch):
    monkeypatch.setattr(config.auth, "auth_mode", "dev")
    monkeypatch.setattr(config.auth, "ws_auth_allowlist_dev", ["query_token", "anon_token"])
    monkeypatch.setattr(config.auth, "enable_legacy_ws_token_auth", True)
    from service.main import app

    class FakeRedis:
        def __init__(self):
            self.xack_called_with = []

        async def xgroup_create(self, stream, group, id="0", mkstream=False):
            return True

        async def xrange(self, stream, start, end, count=100):
            return []

        async def xpending(self, stream, group):
            return {"count": 1}

        async def xautoclaim(self, stream, group, consumer, min_idle_ms, start_id, count=100):
            return ("2-0", [("2-0", {"data": json.dumps({"event": "claimed", "seq": 2})})])

        async def xread(self, streams=None, count=10, timeout=0):
            return []

        async def xack(self, stream, group, message_id):
            self.xack_called_with.append(message_id)

    fake_redis = FakeRedis()
    app.dependency_overrides[get_optional_redis_session_store] = lambda: _FakeSessionStore()
    app.dependency_overrides[get_optional_redis_client] = lambda: fake_redis
    app.dependency_overrides[get_app_container] = _make_fake_container

    try:
        client = TestClient(app)
        with client.websocket_connect("/api/chats/thread-pending/ws?token=good-token") as ws:
            msg = ws.receive_json()
            assert msg.get("type") == "claimed"
            assert msg.get("data", {}).get("event") == "claimed"

        assert "2-0" in fake_redis.xack_called_with
    finally:
        app.dependency_overrides.pop(get_optional_redis_session_store, None)
        app.dependency_overrides.pop(get_optional_redis_client, None)
        app.dependency_overrides.pop(get_app_container, None)
