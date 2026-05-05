import asyncio
import pytest

from tests.test_helpers import FakeAsyncRedis
from service.infrastructure.messaging import worker_consumer


class OneMessageRedis(FakeAsyncRedis):
    def __init__(self, msg_id="1-0", mapping=None):
        super().__init__()
        self._returned = False
        self._msg = (msg_id, mapping or {"data": "hello"})

    async def xread_group(self, group, consumer, streams=None, count=1, timeout=0):
        if not self._returned:
            self._returned = True
            return [
                (
                    list(streams.keys())[0],
                    [self._msg],
                )
            ]
        return []


@pytest.mark.asyncio
async def test_consume_once_acks_on_success():
    redis = OneMessageRedis()
    processed = []

    async def process_func(msg_id, mapping):
        processed.append((msg_id, mapping))
        return True

    n = await worker_consumer.consume_once(redis, "mystream", "mygroup", "consumer-1", process_func)
    assert n == 1
    # confirm ack recorded
    assert ("ACK", "mystream", "mygroup", "1-0") in redis.published


@pytest.mark.asyncio
async def test_consume_once_no_ack_on_exception():
    redis = OneMessageRedis()

    async def process_func(msg_id, mapping):
        raise RuntimeError("fail")

    n = await worker_consumer.consume_once(redis, "mystream", "mygroup", "consumer-1", process_func)
    assert n == 0
    # no ACK recorded
    assert not redis.published


@pytest.mark.asyncio
async def test_consume_loop_stops_on_cancel():
    redis = OneMessageRedis()
    processed = []

    async def process_func(msg_id, mapping):
        processed.append((msg_id, mapping))
        return True

    task = asyncio.create_task(
        worker_consumer.consume_loop(
            redis,
            "mystream",
            "mygroup",
            "consumer-1",
            process_func,
            poll_interval=0.01,
        )
    )
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert processed
