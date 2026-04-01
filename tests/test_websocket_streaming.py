import threading

from fastapi.testclient import TestClient

from orchestrator.app import app
from orchestrator.services.tasks import TaskStatus


def test_websocket_streams_new_events_without_duplicates():
    client = TestClient(app)

    resp = client.post("/task", params={"run": "false"}, json={"prompt": "ws demo"})
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    with client.websocket_connect(f"/ws/task/{task_id}") as websocket:
        initial = websocket.receive_json()
        assert initial["last_seq"] >= 1
        messages = [evt["message"] for evt in initial["events"]]
        assert "Task accepted" in messages

        # Push a new event and expect it once
        post_resp = client.post(
            f"/task/{task_id}/events",
            json={
                "source": "worker",
                "message": "hello ws",
                "level": "info",
                "status": TaskStatus.RUNNING.value,
                "meta": {},
            },
        )
        assert post_resp.status_code == 202

        # Guard against hanging in case of regression
        timer = threading.Timer(2.0, websocket.close)
        timer.start()
        try:
            next_payload = websocket.receive_json()
        finally:
            timer.cancel()

        assert next_payload["last_seq"] > initial["last_seq"]
        assert [evt["message"] for evt in next_payload["events"]] == ["hello ws"]