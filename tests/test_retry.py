import asyncio
import time

import pytest

from orchestrator.utils.retry import retry_async, retry_sync


def test_retry_sync_success_on_second_attempt():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] < 2:
            raise ValueError("fail")
        return "ok"

    t0 = time.time()
    result = retry_sync(fn, retries=3, base_delay=0.01, jitter=0)
    assert result == "ok"
    assert calls["n"] == 2
    assert time.time() - t0 >= 0.01


@pytest.mark.asyncio
async def test_retry_async_success_on_third_attempt():
    calls = {"n": 0}

    async def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("fail")
        return "ok"

    t0 = time.time()
    result = await retry_async(fn, retries=3, base_delay=0.01, jitter=0)
    assert result == "ok"
    assert calls["n"] == 3
    assert time.time() - t0 >= 0.01 + 0.02  # two backoffs


@pytest.mark.asyncio
async def test_retry_async_exhausts_and_raises():
    async def fn():
        raise RuntimeError("always")

    with pytest.raises(RuntimeError):
        await retry_async(fn, retries=2, base_delay=0.001, jitter=0)
