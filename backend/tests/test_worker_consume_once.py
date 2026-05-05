import asyncio

from service.infrastructure.messaging import stream_helpers


def test_worker_consume_once_calls_process_and_acks(monkeypatch):
    """Test that worker_consume_once invokes process_func for each message and acks it."""

    called = []
    acks = []

    async def fake_xread_group(redis_client, group, consumer, streams, count=10, block=0):
        # Return a single message for the requested stream
        return [(list(streams.keys())[0], [("1-0", {"data": "{\"event\": \"test\"}"})])]

    async def fake_xack(redis_client, stream, group, message_id):
        acks.append((stream, group, message_id))

    async def process_func(message_id, fields):
        called.append((message_id, fields))

    monkeypatch.setattr(stream_helpers, "xread_group", fake_xread_group)
    monkeypatch.setattr(stream_helpers, "xack", fake_xack)

    # run the coroutine
    res = asyncio.run(stream_helpers.worker_consume_once(None, "mystream", "mygroup", "mycons", process_func, count=1, block=0))

    assert res == 1
    assert len(called) == 1
    assert called[0][0] == "1-0"
    assert acks == [("mystream", "mygroup", "1-0")]
