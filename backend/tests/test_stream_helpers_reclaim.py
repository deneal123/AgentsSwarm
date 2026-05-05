import pytest
import asyncio
from types import SimpleNamespace

from service.infrastructure.messaging import stream_helpers

class FakeRedisForClaim:
    def __init__(self):
        # entries as list of (id, fields)
        self.entries = [("1-0", {"data": "a"}), ("2-0", {"data": "b"})]
        self.claimed = []
        self.acked = []
    async def xautoclaim(self, stream, group, consumer, min_idle_ms, start_id, count=100):
        # return (next_start, entries)
        return ("3-0", list(self.entries))
    async def xauto_claim(self, *a, **k):
        return list(self.entries)
    async def xack(self, stream, group, message_id):
        self.acked.append(message_id)
        return 1

@pytest.mark.asyncio
async def test_reclaim_and_process_handles_entries_and_acks(monkeypatch):
    fake = FakeRedisForClaim()
    processed = []

    async def process_func(entry_id, fields):
        processed.append((entry_id, fields))

    count = await stream_helpers.reclaim_and_process(fake, "mystream", "mygroup", "consumer1", process_func, min_idle_ms=1000, start_id="0-0", count=100)
    # reclaim_and_process should process both entries
    assert count == 2
    assert len(processed) == 2
    # ack should have been called for each
    assert set(fake.acked) >= {"1-0", "2-0"}
