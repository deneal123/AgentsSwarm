import pytest
from prometheus_client import REGISTRY


@pytest.mark.asyncio
async def test_xadd_error_increments_metric(monkeypatch):
    from service.infrastructure.messaging import stream_helpers

    class FakeRedis:
        def xadd(self, stream, mapping):
            raise RuntimeError("boom")

    fake = FakeRedis()

    # find current metric value
    def get_metric(name):
        # support both canonical name and legacy name without _total
        candidates = [name, name.replace("_total", "")]
        for m in REGISTRY.collect():
            if m.name in candidates:
                if m.samples:
                    return float(m.samples[0].value)
        return 0.0

    before = get_metric("stream_xadd_errors_total")
    with pytest.raises(RuntimeError):
        # sync helper should raise and increment metric
        stream_helpers.xadd_sync(fake, "s", {"data": "x"})
    after = get_metric("stream_xadd_errors_total")
    assert after >= before + 1


@pytest.mark.asyncio
async def test_xautoclaim_failure_increments_metric(monkeypatch):
    from service.infrastructure.messaging import stream_helpers

    class FakeRedis:
        async def xauto_claim(self, *a, **k):
            raise RuntimeError("fail auto")

    fake = FakeRedis()

    def get_metric(name):
        candidates = [name, name.replace("_total", "")]
        for m in REGISTRY.collect():
            if m.name in candidates:
                if m.samples:
                    return float(m.samples[0].value)
        return 0.0

    before = get_metric("stream_xautoclaim_failed_total")
    res = await stream_helpers.xauto_claim(
        fake, "s", "g", "c", min_idle_ms=0, start_id="0-0", count=10
    )
    assert res == []
    after = get_metric("stream_xautoclaim_failed_total")
    assert after >= before + 1


@pytest.mark.asyncio
async def test_reclaim_and_process_increments_processed(monkeypatch):
    import json

    from service.infrastructure.messaging import stream_helpers

    class FakeRedis:
        async def xautoclaim(self, stream, group, consumer, min_idle_ms, start_id, count=100):
            return ("0-0", [("1-0", {"data": json.dumps({"event": "x"})})])

        async def xack(self, stream, group, message_id):
            return 1

    fake = FakeRedis()

    def get_metric(name):
        candidates = [name, name.replace("_total", "")]
        for m in REGISTRY.collect():
            if m.name in candidates:
                if m.samples:
                    return float(m.samples[0].value)
        return 0.0

    before = get_metric("stream_reclaimed_processed_total")

    processed = []

    async def proc(mid, fields):
        processed.append(mid)

    cnt = await stream_helpers.reclaim_and_process(
        fake, "s", "g", "reclaimer", proc, min_idle_ms=0, count=10
    )
    assert cnt == 1
    after = get_metric("stream_reclaimed_processed_total")
    assert after >= before + 1
