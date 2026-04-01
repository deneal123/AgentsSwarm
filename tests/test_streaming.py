from orchestrator.services.streaming import StreamCollector, StreamEvent
from orchestrator.services.tasks import TaskStore


def test_stream_collector_records_and_mirrors_logs():
    ts = TaskStore()
    ts.create_task("t1", "prompt", {})
    collector = StreamCollector(task_store=ts, max_events_per_task=2)

    ev1 = StreamEvent(task_id="t1", source="agent", message="hello", level="info")
    seq1 = collector.record(ev1)

    ev2 = StreamEvent(task_id="t1", source="agent", message="world", level="debug")
    seq2 = collector.record(ev2)

    assert seq2 == seq1 + 1

    events = collector.get_events("t1")
    assert len(events) == 2
    assert events[0].message == "hello"
    assert events[1].message == "world"

    payload = collector.as_payload("t1", after_seq=seq1)
    assert payload["last_seq"] == seq2
    assert len(payload["events"]) == 1
    assert payload["events"][0]["message"] == "world"
    assert "ts" in payload["events"][0]

    task = ts.get_task("t1")
    assert task
    assert task.logs == ["[info] agent: hello", "[debug] agent: world"]


def test_stream_collector_cap_trims_old():
    collector = StreamCollector(max_events_per_task=1)
    collector.record(StreamEvent(task_id="t2", source="a", message="first"))
    collector.record(StreamEvent(task_id="t2", source="a", message="second"))
    events = collector.get_events("t2")
    assert len(events) == 1
    assert events[0].message == "second"
