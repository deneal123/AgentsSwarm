from fastapi.testclient import TestClient

from orchestrator.app import create_app
from orchestrator.services.tasks import TaskStatus


def test_internal_error_is_streamed_to_task_events():
    # Enable debug route and build isolated app instance
    app = create_app(enable_debug_routes=True)
    client = TestClient(app, raise_server_exceptions=False)

    # Create task without auto-run to avoid background noise
    resp = client.post("/task", params={"run": "false"}, json={"prompt": "boom"})
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    # Trigger debug crash
    crash_resp = client.get(f"/debug/crash/{task_id}")
    assert crash_resp.status_code == 500

    # Error should be mirrored to task events with user-facing flag
    ev_resp = client.get(f"/task/{task_id}/events")
    assert ev_resp.status_code == 200
    events = ev_resp.json()["events"]
    messages = [evt["message"] for evt in events]
    assert any("Внутренняя ошибка" in m for m in messages)
    user_error_events = [e for e in events if e["meta"].get("user_facing")]
    assert user_error_events, "Expected user-facing error event"
    assert user_error_events[0]["meta"]["code"] == "internal_error"

    # Task status remains pending since we did not run it
    status_resp = client.get(f"/task/{task_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["task"]["status"] == TaskStatus.PENDING.value