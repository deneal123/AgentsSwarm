import json

from fastapi.testclient import TestClient


def _make_app_and_container_patches():
    from service.main import app
    from service import container

    class FakeSessionStore:
        async def get_session_by_token(self, token):
            if token == "good-token":
                return {"id": "s1", "user_id": "u1"}
            return None

    class FakeAsyncRedis:
        def __init__(self):
            self.xack_called_with = []

        async def xgroup_create(self, stream, group, id="0", mkstream=False):
            return True

        async def xrange(self, stream, start, end, count=100):
            return [("1-0", {"data": json.dumps({"event": "replay", "seq": 1})})]

        async def xpending(self, stream, group):
            return {"count": 0}

        async def xautoclaim(self, stream, group, consumer, min_idle_ms, start_id, count=100):
            return ("2-0", [("2-0", {"data": json.dumps({"event": "claimed", "seq": 2})})])

        async def xread(self, streams=None, count=10, timeout=0):
            return []

        async def xack(self, stream, group, message_id):
            self.xack_called_with.append(message_id)

    fake_redis = FakeAsyncRedis()
    container._CONTAINER[container.RedisSessionStoreName] = FakeSessionStore()
    container._CONTAINER[container.RedisClientName] = fake_redis
    container._CONTAINER[container.JobServiceName] = None
    return app, fake_redis


def test_replay_with_last_id():
    app, _ = _make_app_and_container_patches()
    client = TestClient(app)

    with client.websocket_connect("/api/chats/thread-replay/ws?token=good-token&last_id=0-0") as ws:
        msg = ws.receive_json()
        assert msg.get("type") == "replay"
        assert msg.get("data", {}).get("event") == "replay"


def test_claim_pending_on_reconnect():
    from service.main import app
    from service import container

    class FakeSessionStore:
        async def get_session_by_token(self, token):
            if token == "good-token":
                return {"id": "s1", "user_id": "u1"}
            return None

    class FakeAsyncRedis2:
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

    fake_redis2 = FakeAsyncRedis2()
    container._CONTAINER[container.RedisSessionStoreName] = FakeSessionStore()
    container._CONTAINER[container.RedisClientName] = fake_redis2
    container._CONTAINER[container.JobServiceName] = None

    client = TestClient(app)
    with client.websocket_connect("/api/chats/thread-pending/ws?token=good-token") as ws:
        msg = ws.receive_json()
        assert msg.get("type") == "claimed"
        assert msg.get("data", {}).get("event") == "claimed"

    assert "2-0" in fake_redis2.xack_called_with
