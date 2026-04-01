from fastapi.testclient import TestClient

from orchestrator.app import app
from orchestrator.services.tasks import TaskStatus


def test_ingest_event_updates_status_and_stream():
    client = TestClient(app)

    # Create task
    resp = client.post("/task", json={"prompt": "move robot"})
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    # Ingest event with status update
    ev_resp = client.post(
        f"/task/{task_id}/events",
        json={
            "source": "worker",
            "message": "started",
            "level": "info",
            "status": "running",
            "meta": {"worker": "w1"},
        },
    )
    assert ev_resp.status_code == 202
    ack = ev_resp.json()
    assert ack["task_id"] == task_id
    assert ack["seq"] >= 2  # task accepted is seq1
    assert ack["status"] == "running"

    # Status endpoint reflects update
    status_resp = client.get(f"/task/{task_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["task"]["status"] == "running"

    # Events endpoint returns ingested event
    events_resp = client.get(f"/task/{task_id}/events", params={"after_seq": 0})
    assert events_resp.status_code == 200
    data = events_resp.json()
    messages = [e["message"] for e in data["events"]]
    assert "started" in messages
    worker_events = [e for e in data["events"] if e["source"] == "worker"]
    assert worker_events
    assert worker_events[0]["message"] == "started"
    assert worker_events[0]["meta"]["worker"] == "w1"


def test_cancel_emits_event_and_sets_status():
    client = TestClient(app)
    resp = client.post("/task", params={"run": "false"}, json={"prompt": "cancel me"})
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    cancel_resp = client.post(f"/task/{task_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == TaskStatus.CANCELED.value

    status_resp = client.get(f"/task/{task_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["task"]["status"] == TaskStatus.CANCELED.value

    events_resp = client.get(f"/task/{task_id}/events")
    assert events_resp.status_code == 200
    messages = [e["message"] for e in events_resp.json()["events"]]
    assert "Task canceled" in messages
