import pytest
import pytest
import json
from prometheus_client import REGISTRY

from service.presentation.routers import chat_ws, jobs_ws


class FakeWebSocket:
    def __init__(self, send_fail_on=None):
        # send_fail_on can be a set of entry_ids that will raise when send_json called
        self.send_fail_on = set(send_fail_on or [])
        self.sent = []
        self.query_params = {"token": "t"}
        self.headers = {}
        self.cookies = {}

    async def send_json(self, payload):
        eid = payload.get("id")
        if eid in self.send_fail_on:
            raise RuntimeError("send failed")
        self.sent.append(payload)


class FakeRedis:
    def __init__(self):
        self.acked = []

    async def xack(self, stream, group, message_id):
        if message_id == "bad-ack":
            raise RuntimeError("ack failed")
        self.acked.append(message_id)
        return 1


def get_metric(name):
    candidates = [name, name.replace("_total", "")]
    for m in REGISTRY.collect():
        if m.name in candidates:
            if m.samples:
                return float(m.samples[0].value)
    return 0.0


@pytest.mark.asyncio
async def test_chat_claimed_metrics(monkeypatch):
    fake_ws = FakeWebSocket(send_fail_on={"1-0"})
    fake_redis = FakeRedis()
    claimed = [("1-0", {"data": json.dumps({"event": "one"})}), ("2-0", {"data": json.dumps({"event": "two"})})]

    before_sent = get_metric("chat_claimed_sent_total")
    before_left = get_metric("chat_claimed_left_unacked_total")
    before_xack = get_metric("chat_xack_errors_total")

    await chat_ws.process_claimed_entries(fake_ws, fake_redis, "chat:s", "g", claimed)

    after_sent = get_metric("chat_claimed_sent_total")
    after_left = get_metric("chat_claimed_left_unacked_total")
    after_xack = get_metric("chat_xack_errors_total")

    # one success, one left unacked
    assert after_sent >= before_sent + 1
    assert after_left >= before_left + 1
    # ack errors should be zero
    assert after_xack >= before_xack
    # acked list should contain only the successful id
    assert fake_redis.acked == ["2-0"]


@pytest.mark.asyncio
async def test_jobs_claimed_metrics_and_xack_error(monkeypatch):
    fake_ws = FakeWebSocket(send_fail_on=set())
    fake_redis = FakeRedis()
    # include an entry that will cause xack to fail
    claimed = [("good-1", {"data": json.dumps({"event": "ok"})}), ("bad-ack", {"data": json.dumps({"event": "failack"})})]

    before_sent = get_metric("jobs_claimed_sent_total")
    before_left = get_metric("jobs_claimed_left_unacked_total")
    before_xack = get_metric("jobs_xack_errors_total")

    await jobs_ws.process_jobs_claimed_entries(fake_ws, fake_redis, "job:s", "g", claimed)

    after_sent = get_metric("jobs_claimed_sent_total")
    after_left = get_metric("jobs_claimed_left_unacked_total")
    after_xack = get_metric("jobs_xack_errors_total")

    # both sends should be counted as sent
    assert after_sent >= before_sent + 2
    # none left unacked because sends didn't fail
    assert after_left >= before_left
    # xack errors incremented by 1 for bad-ack
    assert after_xack >= before_xack + 1
