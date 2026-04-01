from fastapi.testclient import TestClient

from orchestrator.app import app


def test_health_endpoint():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert "version" in payload
    assert "redis" in payload
    assert payload["redis"]["status"] in {"disabled", "ok", "error"}


def test_events_endpoint_returns_initial_event():
    client = TestClient(app)
    resp = client.post("/task", json={"prompt": "test"})
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    ev_resp = client.get(f"/task/{task_id}/events")
    assert ev_resp.status_code == 200
    data = ev_resp.json()
    assert data["task_id"] == task_id
    assert data["last_seq"] >= 1
    assert len(data["events"]) >= 1
    assert data["events"][0]["message"].lower().startswith("task accepted")
