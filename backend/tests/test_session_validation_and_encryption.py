import pytest
from pydantic import ValidationError
from cryptography.fernet import Fernet

from service.services.agents.infrastructure.sessions import PseudoSession, RedisSession


@pytest.mark.asyncio
async def test_pseudo_session_validation_raises():
    s = PseudoSession("tv")
    with pytest.raises(ValidationError):
        await s.add_items([{"role": "invalid", "content": 123}])


@pytest.mark.asyncio
async def test_redis_session_encryption_and_decryption():
    class FakeRedis:
        def __init__(self):
            self.data = {}

        async def rpush(self, key, *values):
            self.data.setdefault(key, [])
            self.data[key].extend(values)

        async def lrange(self, key, start, end):
            return self.data.get(key, [])

        async def ltrim(self, key, start, end):
            arr = self.data.get(key, [])
            if start < 0:
                start = max(len(arr) + start, 0)
            if end < 0:
                end = len(arr) + end + 1
            self.data[key] = arr[start:end]

        async def expire(self, key, seconds):
            pass

        async def rpop(self, key):
            arr = self.data.get(key, [])
            if not arr:
                return None
            return arr.pop()

        async def delete(self, key):
            self.data.pop(key, None)

    key = Fernet.generate_key()
    r = FakeRedis()
    s = RedisSession("sid_enc", client=r)
    s._encryption_key = key

    await s.add_items([{"role": "user", "content": "secret"}])
    items = await s.get_items()
    assert items[0]["content"] == "secret"
