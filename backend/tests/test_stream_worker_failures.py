import json

import pytest


@pytest.mark.asyncio
async def test_process_func_failure_does_not_ack(monkeypatch):
    """If process_func raises, worker should not xack the message."""
    from service.infrastructure.messaging import stream_helpers

    class FakeRedis:
        def __init__(self):
            self.read_calls = 0
            self.acked = []

        async def xread_group(self, group, consumer, streams, count=10, timeout=0):
            if self.read_calls == 0:
                self.read_calls += 1
                return [
                    (
                        "batch:err:stream",
                        [("100-0", {"data": json.dumps({"event": "p"})})],
                    )
                ]
            return []

        async def xack(self, stream, group, message_id):
            self.acked.append(message_id)

    fake = FakeRedis()

    async def failing_processor(msg_id, fields):
        raise RuntimeError("processing failed")

    # Run a single iteration using worker_consume_once
    processed = await stream_helpers.worker_consume_once(
        fake, "batch:err:stream", "g", "c", failing_processor, count=1, block=0
    )
    # processed should be 0 and no ack recorded
    assert processed == 0
    assert fake.acked == []


@pytest.mark.asyncio
async def test_reclaim_and_process_xautoclaim(monkeypatch):
    """xauto_claim returns entries, they are processed and xacked."""
    from service.infrastructure.messaging import stream_helpers

    class FakeRedisClaim:
        def __init__(self):
            self.xautoclaim_called = False
            self.acked = []

        async def xautoclaim(self, stream, group, consumer, min_idle_ms, start_id, count=100):
            self.xautoclaim_called = True
            return ("next-id", [("200-0", {"data": json.dumps({"event": "reclaimed"})})])

        async def xack(self, stream, group, message_id):
            self.acked.append(message_id)

    fake = FakeRedisClaim()

    processed = []

    async def proc(msg_id, fields):
        processed.append((msg_id, fields))

    cnt = await stream_helpers.reclaim_and_process(
        fake,
        "batch:reclaim:stream",
        "g",
        "consumer-1",
        proc,
        min_idle_ms=1000,
        count=10,
    )

    assert cnt == 1
    assert processed and processed[0][0] == "200-0"
    assert "200-0" in fake.acked
