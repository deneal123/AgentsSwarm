import asyncio
import json
import pytest

from service.agents.sessions import RedisSession


class FakeRedis:
    def __init__(self):
        self.data = {}

    async def lrange(self, key, start, end):
        return self.data.get(key, [])

    async def rpush(self, key, *values):
        self.data.setdefault(key, [])
        self.data[key].extend(values)

    async def ltrim(self, key, start, end):
        arr = self.data.get(key, [])
        # negative indices handling similar to redis
        if start < 0:
            start = max(len(arr) + start, 0)
        if end < 0:
            end = len(arr) + end + 1
        self.data[key] = arr[start:end]

    async def expire(self, key, seconds):
        # no-op for test
        pass

    async def rpop(self, key):
        arr = self.data.get(key, [])
        if not arr:
            return None
        return arr.pop()

    async def delete(self, key):
        self.data.pop(key, None)


@pytest.mark.asyncio
async def test_redis_session_add_get_pop_limit():
    r = FakeRedis()
    s = RedisSession("sid1", client=r, ttl_seconds=60, max_items=3, prefix="testpref")

    await s.add_items([{"role": "user", "content": "a"}])
    await s.add_items([{"role": "assistant", "content": "b"}])
    await s.add_items([{"role": "user", "content": "c"}])
    await s.add_items([{"role": "assistant", "content": "d"}])

    # max_items=3 should keep only last 3
    items = await s.get_items()
    assert len(items) == 3
    assert items[0]["content"] == "b"
    assert items[-1]["content"] == "d"

    last = await s.pop_item()
    assert last["content"] == "d"

    # clear
    await s.clear_session()
    assert await s.get_items() == []


@pytest.mark.asyncio
async def test_redis_session_from_container(monkeypatch):
    r = FakeRedis()

    def fake_get(name: str):
        return r

    monkeypatch.setattr("service.container.get", lambda name: r)

    s = RedisSession.from_container("sid2", max_items=2)
    # client should work via container
    await s.add_items([{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}, {"role": "user", "content": "z"}])
    items = await s.get_items()
    assert len(items) == 2
