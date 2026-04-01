from fastapi.testclient import TestClient

from orchestrator.app import app


def test_plan_endpoint_returns_plan():
    client = TestClient(app)
    resp = client.post("/task", json={"prompt": "multi-step task"})
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    plan_resp = client.get(f"/task/{task_id}/plan")
    assert plan_resp.status_code == 200
    payload = plan_resp.json()
    assert payload["task_id"] == task_id
    assert isinstance(payload["plan"], list)
    assert len(payload["plan"]) >= 1
    first = payload["plan"][0]
    assert {"id", "description", "agent", "status", "meta"}.issubset(first.keys())
    assert first["status"] in {"pending", "running", "completed"}
    assert "expected_outcome" in first["meta"]
    assert "tools" in first["meta"]
