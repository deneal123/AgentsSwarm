import asyncio
import json

import pytest


async def _run_worker_once(redis, process_func):
    # helper: run a single iteration using worker_consume_once
    from service.infrastructure.messaging.stream_helpers import worker_consume_once

    await worker_consume_once(
        redis_client=redis,
        stream="batch:xyz:stream",
        group="batch:xyz:group",
        consumer="worker-1",
        process_func=process_func,
        count=5,
        block=0,
    )


class FakeRedisForWorker:
    def __init__(self):
        self.read_calls = 0
        self.acked = []

    async def xread_group(self, group, consumer, streams, count=10, timeout=0):
        # Return one batch first time, then empty
        if self.read_calls == 0:
            self.read_calls += 1
            return [
                (
                    "batch:xyz:stream",
                    [
                        ("10-0", {"data": json.dumps({"event": "p", "v": 1})}),
                        ("11-0", {"data": json.dumps({"event": "p", "v": 2})}),
                    ],
                )
            ]
        await asyncio.sleep(0)
        return []

    async def xack(self, stream, group, message_id):
        self.acked.append(message_id)


@pytest.mark.asyncio
async def test_worker_processes_and_acks(monkeypatch):
    fake = FakeRedisForWorker()

    processed = []

    async def fake_processor(msg_id, fields):
        processed.append((msg_id, fields))

    # Run worker loop once
    await _run_worker_once(fake, fake_processor)

    # Ensure both messages were processed
    assert ("10-0", {"data": json.dumps({"event": "p", "v": 1})}) in processed
    assert ("11-0", {"data": json.dumps({"event": "p", "v": 2})}) in processed
    # Ensure both ACKed
    assert "10-0" in fake.acked and "11-0" in fake.acked
