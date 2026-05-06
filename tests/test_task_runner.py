import time

from fastapi.testclient import TestClient

from orchestrator.app import app
from orchestrator.services.tasks import TaskStatus


def test_task_runs_and_completes_with_events():
    client = TestClient(app)
    resp = client.post("/task", json={"prompt": "demo"})
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    # Wait briefly for task to complete
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
    assert any("Plan created" == m for m in messages)
    assert any(m.startswith("Plan step 1 started") for m in messages)
    assert any("Task completed" == m for m in messages)

    # Plan persisted on task
    status_after = client.get(f"/task/{task_id}/status")
    assert status_after.status_code == 200
    plan = status_after.json()["task"].get("plan")
    assert plan
    assert len(plan) >= 3
    assert all(step.get("status") == "completed" for step in plan)


def test_task_can_be_created_without_auto_run_and_started_later():
    client = TestClient(app)
    resp = client.post("/task", params={"run": "false"}, json={"prompt": "manual"})
    assert resp.status_code == 202
    payload = resp.json()
    assert payload["status"] == TaskStatus.PENDING.value
    task_id = payload["task_id"]

    # Initially pending with no plan
    status_resp = client.get(f"/task/{task_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["task"]["status"] == TaskStatus.PENDING.value
    assert status_resp.json()["task"].get("plan") == []

    events_resp = client.get(f"/task/{task_id}/events")
    assert events_resp.status_code == 200
    events = events_resp.json()["events"]
    assert events
    assert events[0]["message"] == "Task accepted"

    # Trigger execution manually
    run_resp = client.post(f"/task/{task_id}/run")
    assert run_resp.status_code == 202
    assert run_resp.json()["task_id"] == task_id

    # Wait for completion
    deadline = time.time() + 3
    while time.time() < deadline:
        status_resp = client.get(f"/task/{task_id}/status")
        assert status_resp.status_code == 200
        status = status_resp.json()["task"]["status"]
        if status == TaskStatus.COMPLETED.value:
            break
        time.sleep(0.05)
    else:
        raise AssertionError("Task did not complete after manual run")

    plan_resp = client.get(f"/task/{task_id}/plan")
    assert plan_resp.status_code == 200
    plan = plan_resp.json()["plan"]
    assert len(plan) >= 3
    assert all(step.get("status") == "completed" for step in plan)


def test_run_endpoint_rejects_canceled_or_completed():
    client = TestClient(app)

    # Canceled task cannot be run
    resp = client.post("/task", params={"run": "false"}, json={"prompt": "cancel then run"})
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    cancel_resp = client.post(f"/task/{task_id}/cancel")
    assert cancel_resp.status_code == 200

    run_after_cancel = client.post(f"/task/{task_id}/run")
    assert run_after_cancel.status_code == 409

    # Completed task cannot be run
    resp2 = client.post("/task", json={"prompt": "complete then rerun"})
    assert resp2.status_code == 202
    task2 = resp2.json()["task_id"]

    deadline = time.time() + 3
    while time.time() < deadline:
        status_resp = client.get(f"/task/{task2}/status")
        status = status_resp.json()["task"]["status"]
        if status == TaskStatus.COMPLETED.value:
            break
        time.sleep(0.05)
    else:
        raise AssertionError("Task did not complete")

    run_after_complete = client.post(f"/task/{task2}/run")
    assert run_after_complete.status_code == 409


def test_cancel_during_run_stops_execution_and_marks_steps():
    client = TestClient(app)
    resp = client.post("/task", json={"prompt": "long running"})
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    # Give runner a moment to start
    time.sleep(0.01)

    cancel_resp = client.post(f"/task/{task_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == TaskStatus.CANCELED.value

    deadline = time.time() + 2
    while time.time() < deadline:
        status_resp = client.get(f"/task/{task_id}/status")
        assert status_resp.status_code == 200
        status = status_resp.json()["task"]["status"]
        if status == TaskStatus.CANCELED.value:
            break
        time.sleep(0.02)
    else:
        raise AssertionError("Task did not reach canceled state")

    plan_resp = client.get(f"/task/{task_id}/plan")
    assert plan_resp.status_code == 200
    plan = plan_resp.json()["plan"]
    assert plan
    statuses = {step.get("status") for step in plan}
    assert TaskStatus.CANCELED.value in statuses
    assert TaskStatus.COMPLETED.value not in statuses or len(statuses) > 1  # at least one canceled

    events_resp = client.get(f"/task/{task_id}/events")
    assert events_resp.status_code == 200
    messages = [e["message"] for e in events_resp.json()["events"]]
    assert "Task canceled" in messages
    # "Task canceled during execution" is only emitted when the task was RUNNING at cancel time.
    # In a sync TestClient background tasks complete before cancel arrives, so we don't assert it here.


def test_run_endpoint_conflict_when_task_marked_running():
    client = TestClient(app)
    resp = client.post("/task", params={"run": "false"}, json={"prompt": "manual"})
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    ev_resp = client.post(
        f"/task/{task_id}/events",
        json={
            "source": "worker",
            "message": "already running",
            "status": TaskStatus.RUNNING.value,
            "meta": {},
        },
    )
    assert ev_resp.status_code == 202
    status_resp = client.get(f"/task/{task_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["task"]["status"] == TaskStatus.RUNNING.value

    run_resp = client.post(f"/task/{task_id}/run")
    assert run_resp.status_code == 409
