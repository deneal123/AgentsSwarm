import pytest
import json


@pytest.mark.asyncio
async def test_ws_crash_then_reclaim_e2e():
    """Simulate a websocket consumer that fails to send one claimed entry, leaving it unacked,
    then run reclaim_and_process to ensure it gets processed and acked by the reclaimer.
    """
    from service.infrastructure.messaging import stream_helpers
    from service.presentation.routers import chat_ws

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
            return True

        async def xread_group(self, group, consumer, streams=None, count=10, timeout=0):
            # return entries and mark them as pending for the group
            res = []
            for sname, _ in (streams or {}).items():
                lst = list(self.storage.get(sname, []))
                if not lst:
                    continue
                pend = self.pending.setdefault(group, {})
                for entry_id, fields in lst:
                    if entry_id not in pend:
                        pend[entry_id] = (fields, consumer)
                res.append((sname, list(lst)))
            return res

        async def xack(self, stream, group, message_id):
            pend = self.pending.get(group, {})
            if message_id in pend:
                del pend[message_id]
            self.acked.append(message_id)
            return 1

        async def xpending(self, stream, group):
            pend = self.pending.get(group, {})
            return {"count": len(pend)}

        async def xautoclaim(self, stream, group, consumer, min_idle_ms, start_id, count=100):
            pend = self.pending.get(group, {})
            entries = []
            for eid, (fields, orig_consumer) in list(pend.items()):
                entries.append((eid, fields))
                del pend[eid]
            return ("0-0", entries)

    fake = FakeRedisReclaim()

    stream = "ws-crash:stream"
    group = "ws-crash:group"
    consumer = "ws-consumer"

    # add two messages
    id1 = fake.xadd(stream, {"data": json.dumps({"event": "one"})})
    id2 = fake.xadd(stream, {"data": json.dumps({"event": "two"})})

    # mark them pending by doing a read (simulates consumer reading but failing to ack)
    await stream_helpers.worker_consume_once(fake, stream, group, consumer, lambda *_: (_ for _ in ()).throw(RuntimeError("fail")), count=10, block=0)

    pend = await stream_helpers.xpending(fake, stream, group)
    assert pend.get("count", 0) == 2

    # Now simulate websocket processing claimed entries: it will fail on id2
    class FailingWS:
        def __init__(self, fail_on):
            self.fail_on = set(fail_on)
            self.sent = []

        async def send_json(self, obj):
            eid = obj.get("id")
            if eid in self.fail_on:
                raise RuntimeError("ws send failed")
            self.sent.append(obj)

    # prepare claimed entries list from pending without removing them (simulate xauto_claim that returns entries)
    pend_map = fake.pending.get(group, {})
    claimed = [(eid, fields) for eid, (fields, _c) in pend_map.items()]

    ws = FailingWS(fail_on={id2})
    # process claimed entries via chat_ws helper (this should ack only id1)
    await chat_ws.process_claimed_entries(ws, fake, stream, group, claimed)

    # assert one acked, one left pending
    assert id1 in fake.acked
    pend_after = await stream_helpers.xpending(fake, stream, group)
    assert pend_after.get("count", 0) == 1

    # Now run reclaim_and_process to process remaining pending entries
    processed = []

    async def good_proc(mid, fields):
        processed.append(mid)

    cnt = await stream_helpers.reclaim_and_process(fake, stream, group, "reclaimer", good_proc, min_idle_ms=0, count=100)
    assert cnt == 1
    assert id2 in processed
    assert id2 in fake.acked
