import pytest

from service.utils.file_scan_worker import process_scan_once


class FakeRedis:
    def __init__(self, to_pop=None):
        self.to_pop = to_pop or []
        self.published = []

    def lpop(self, key):
        if self.to_pop:
            return self.to_pop.pop(0)
        return None

    def xadd(self, key, mapping):
        self.published.append((key, mapping))


class FakeScanner:
    def __init__(self):
        self.scanned = []

    async def scan(self, file_key: str):
        self.scanned.append(file_key)
        return {"status": "ok", "file_key": file_key}


@pytest.mark.asyncio
async def test_process_scan_once_publishes_result():
    fake_redis = FakeRedis(to_pop=[b"folder/file.jpg"])
    scanner = FakeScanner()

    res = await process_scan_once(fake_redis, scanner)
    assert res == 1
    assert scanner.scanned == ["folder/file.jpg"]
    assert len(fake_redis.published) == 1


@pytest.mark.asyncio
async def test_process_scan_once_no_item():
    fake_redis = FakeRedis(to_pop=[])
    scanner = FakeScanner()

    res = await process_scan_once(fake_redis, scanner)
    assert res == 0
