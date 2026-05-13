import json

import pytest


@pytest.mark.asyncio
async def test_reclaim_e2e_flow():
    """End-to-end style test: message read by a consumer that fails to ack, then reclaimed and processed."""
    from service.infrastructure.messaging import stream_helpers

    class FakeRedisReclaim:
        def __init__(self):
            self.storage = {}  # stream -> list of (id, mapping)
            self._counters = {}
            # pending: group -> {id: (fields, consumer)}
            self.pending = {}
            self.acked = []

        def _next_id(self, stream):
            v = self._counters.get(stream, 0) + 1
            self._counters[stream] = v
            return f"{v}-0"

        def xadd(self, stream, mapping):
            lst = self.storage.setdefault(stream, [])
            _id = self._next_id(stream)
            lst.append((_id, dict(mapping)))
            return _id

        async def xgroup_create(self, stream, group, id="0", mkstream=False):
            # no-op
            return True

        async def xread_group(self, group, consumer, streams=None, count=10, timeout=0):
            # simplistic: return all entries and mark them as pending for the group
            res = []
            for sname, _id in (streams or {}).items():
                lst = list(self.storage.get(sname, []))
                if not lst:
                    continue
                # mark pending
                pend = self.pending.setdefault(group, {})
                for entry_id, fields in lst:
                    # don't duplicate pending if already present
                    if entry_id not in pend:
                        pend[entry_id] = (fields, consumer)
                res.append((sname, list(lst)))
            return res

        async def xack(self, stream, group, message_id):
            # simulate ack by removing from pending and recording
            pend = self.pending.get(group, {})
            if message_id in pend:
                del pend[message_id]
            self.acked.append(message_id)
            return 1

        async def xpending(self, stream, group):
            pend = self.pending.get(group, {})
            return {"count": len(pend)}

        async def xautoclaim(self, stream, group, consumer, min_idle_ms, start_id, count=100):
            # return all pending entries for the group as claimed and remove them from pending
            pend = self.pending.get(group, {})
            entries = []
            for eid, (fields, _orig_consumer) in list(pend.items()):
                entries.append((eid, fields))
                del pend[eid]
            # mimic (next_start, entries) signature
            return ("0-0", entries)

    fake = FakeRedisReclaim()

    stream = "reclaim:e2e:stream"
    group = "reclaim:e2e:group"
    consumer1 = "consumer-failed"

    # add two messages
    id1 = fake.xadd(stream, {"data": json.dumps({"event": "one"})})
    id2 = fake.xadd(stream, {"data": json.dumps({"event": "two"})})

    # simulate a consumer that reads and fails to process (so no ack)
    async def failing_proc(mid, fields):
        raise RuntimeError("simulated failure")

    # run one consume iteration which will mark pending via xread_group
    processed = await stream_helpers.worker_consume_once(
        fake, stream, group, consumer1, failing_proc, count=10, block=0
    )
    assert processed == 0

    pend = await stream_helpers.xpending(fake, stream, group)
    assert pend.get("count", 0) == 2

    # now reclaim and process with a working processor
    processed_items = []

    async def good_proc(mid, fields):
        processed_items.append((mid, fields))

    cnt = await stream_helpers.reclaim_and_process(
        fake,
        stream,
        group,
        "reclaimer",
        good_proc,
        min_idle_ms=0,
        count=100,
    )

    assert cnt == 2
    # ensure processed items correspond to our ids
    ids = [p[0] for p in processed_items]
    assert id1 in ids and id2 in ids
    # ensure ack recorded
    assert id1 in fake.acked and id2 in fake.acked
