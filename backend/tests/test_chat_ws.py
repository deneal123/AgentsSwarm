import json

from fastapi.testclient import TestClient
from service.settings import config



def test_chat_ws_reconnect_replay_and_pending_for_auth_user(monkeypatch):
    monkeypatch.setattr(config.auth, "auth_mode", "dev")
    monkeypatch.setattr(config.auth, "ws_auth_allowlist_dev", ["query_token", "anon_token"])
    monkeypatch.setattr(config.auth, "enable_legacy_ws_token_auth", True)
    from service.main import app
    from service import container

    class FakeSessionStore:
        async def get_session_by_token(self, token):
            if token == "good-token":
                return {"id": "s1", "user_id": "u1"}
            return None

    class FakeRedis:
        def __init__(self):
            self.xack_called_with = []

        async def xgroup_create(self, stream, group, id="0", mkstream=False):
            return True

        async def xrange(self, stream, start, end, count=100):
            return [("1-0", {"data": json.dumps({"event": "replay", "seq": 1})})]

        async def xpending(self, stream, group):
            return {"count": 1}

        async def xautoclaim(self, stream, group, consumer, min_idle_ms, start_id, count=100):
            return ("2-0", [("2-0", {"data": json.dumps({"event": "claimed", "seq": 2})})])

        async def xack(self, stream, group, message_id):
            self.xack_called_with.append(message_id)

        async def xread(self, streams=None, count=10, timeout=0):
            return []

    container._CONTAINER[container.RedisSessionStoreName] = FakeSessionStore()
    fake_redis = FakeRedis()
    container._CONTAINER[container.RedisClientName] = fake_redis
    container._CONTAINER[container.JobServiceName] = None

    client = TestClient(app)

    with client.websocket_connect("/api/chats/T1/ws?token=good-token&last_id=0-0") as ws:
        replay = ws.receive_json()
        claimed = ws.receive_json()
        assert replay["type"] == "replay"
        assert replay["data"]["event"] == "replay"
        assert claimed["type"] == "claimed"
        assert claimed["data"]["event"] == "claimed"

    assert "2-0" in fake_redis.xack_called_with


def test_chat_ws_guest_skips_pending_and_starts_from_latest(monkeypatch):
    monkeypatch.setattr(config.auth, "auth_mode", "dev")
    monkeypatch.setattr(config.auth, "ws_auth_allowlist_dev", ["query_token", "anon_token"])
    monkeypatch.setattr(config.auth, "enable_legacy_ws_token_auth", True)
    from service.main import app
    from service import container

    class FakeSessionStore:
        async def get_session_by_token(self, token):
            return None

    class FakeRedis:
        def __init__(self):
            self.xpending_calls = 0
            self.xread_calls = []

        async def xgroup_create(self, stream, group, id="0", mkstream=False):
            return True

        async def xpending(self, stream, group):
            self.xpending_calls += 1
            return {"count": 1}

        async def xread(self, streams=None, count=10, timeout=0):
            self.xread_calls.append(streams)
            return []

    container._CONTAINER[container.RedisSessionStoreName] = FakeSessionStore()
    fake_redis = FakeRedis()
    container._CONTAINER[container.RedisClientName] = fake_redis
    container._CONTAINER[container.JobServiceName] = None

    client = TestClient(app)

    with client.websocket_connect("/api/chats/T1/ws?token=anon-token") as ws:
        heartbeat = ws.receive_json()
        assert heartbeat["type"] == "heartbeat"

    assert fake_redis.xpending_calls == 0
    assert any(next(iter(stream.values())) == "$" for stream in fake_redis.xread_calls)


def test_jobs_ws_session_and_stream(monkeypatch):
    monkeypatch.setattr(config.auth, "auth_mode", "dev")
    monkeypatch.setattr(config.auth, "ws_auth_allowlist_dev", ["query_token", "anon_token"])
    monkeypatch.setattr(config.auth, "enable_legacy_ws_token_auth", True)
    from service.main import app
    from service import container

    class FakeSessionStore:
        async def get_session_by_token(self, token):
            if token == "good-token":
                return {"id": "s1", "user_id": "u1"}
            return None

    class FakeAsyncRedis:
        def __init__(self):
            self._called = 0

        async def xread_group(self, group, consumer, streams=None, count=1, timeout=0):
            if self._called == 0:
                self._called += 1
                stream_key = next(iter(streams.keys()))
                return [(stream_key, [("1-0", {"data": json.dumps({"event": "progress", "progress": 30})})])]
            return []

        async def xack(self, stream, group, message_id):
            return None

        async def xgroup_create(self, stream, group, id="0", mkstream=False):
            return None

        async def xpending(self, stream, group):
            return {"count": 0}

    container._CONTAINER[container.RedisSessionStoreName] = FakeSessionStore()
    container._CONTAINER[container.RedisClientName] = FakeAsyncRedis()

    client = TestClient(app)

    with client.websocket_connect("/api/jobs/v1/job-123/ws?token=good-token") as ws:
        msg = ws.receive_json()
        assert isinstance(msg, dict)
        if "data" in msg:
            data = msg["data"]
            assert data.get("event") == "progress"
