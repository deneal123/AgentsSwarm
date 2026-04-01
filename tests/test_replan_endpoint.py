import time

from fastapi.testclient import TestClient

from orchestrator.app import app
from orchestrator.services.tasks import TaskStatus


def test_replan_builds_new_plan_and_resets_status():
    client = TestClient(app)

    resp = client.post("/task", params={"run": "false"}, json={"prompt": "demo"})
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    # initial plan empty
    plan_before = client.get(f"/task/{task_id}/plan").json()["plan"]
    assert plan_before == []

    replan_resp = client.post(f"/task/{task_id}/replan")
    assert replan_resp.status_code == 202
    assert replan_resp.json()["status"] == TaskStatus.PENDING.value

    plan_after = client.get(f"/task/{task_id}/plan").json()["plan"]
    assert len(plan_after) == 3
    assert all(step["status"] == TaskStatus.PENDING.value for step in plan_after)

    # Run after replan
    run_resp = client.post(f"/task/{task_id}/run")
    assert run_resp.status_code == 202

    deadline = time.time() + 3
    while time.time() < deadline:
        status = client.get(f"/task/{task_id}/status").json()["task"]["status"]
        if status == TaskStatus.COMPLETED.value:
            break
        time.sleep(0.05)
    else:
        raise AssertionError("Task did not complete after replan/run")

    plan_final = client.get(f"/task/{task_id}/plan").json()["plan"]
    assert all(step["status"] == TaskStatus.COMPLETED.value for step in plan_final)


def test_replan_conflict_when_running():
    client = TestClient(app)

    resp = client.post("/task", json={"prompt": "demo"})
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    # Immediately try to replan while runner may still be running (race tolerated)
    replan_resp = client.post(f"/task/{task_id}/replan")
    assert replan_resp.status_code in {202, 409}

    if replan_resp.status_code == 409:
        assert replan_resp.json()["detail"] == "Task already running"
    else:
        status = client.get(f"/task/{task_id}/status").json()["task"]["status"]
        assert status == TaskStatus.PENDING.value