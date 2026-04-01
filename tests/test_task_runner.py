import time

from fastapi.testclient import TestClient

from orchestrator.app import app
from orchestrator.services.tasks import TaskStatus


def test_task_runs_and_completes_with_events():
    client = TestClient(app)
    resp = client.post("/task", json={"prompt": "demo"})
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    # Wait briefly for background task to complete
    deadline = time.time() + 3
    while time.time() < deadline:
        status_resp = client.get(f"/task/{task_id}/status")
        assert status_resp.status_code == 200
        status = status_resp.json()["task"]["status"]
        if status == TaskStatus.COMPLETED.value:
            break
        time.sleep(0.05)
    else:
        raise AssertionError("Task did not complete in time")

    events_resp = client.get(f"/task/{task_id}/events")
    assert events_resp.status_code == 200
    events = events_resp.json()["events"]
    messages = [e["message"] for e in events]
    assert "Task accepted" in messages[0]
    assert any("Processing started" == m for m in messages)
    assert any("Task completed" == m for m in messages)
