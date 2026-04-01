from orchestrator.services.tasks import TaskStatus, TaskStore


def test_cancel_incomplete_steps_preserves_completed():
    store = TaskStore()
    store.create_task("t1", "prompt", {})
    store.set_plan(
        "t1",
        [
            {"id": 1, "status": TaskStatus.COMPLETED.value},
            {"id": 2, "status": "running"},
            {"id": 3, "status": "pending"},
        ],
    )

    store.cancel_incomplete_steps("t1")

    plan = store.get_task("t1").plan
    assert plan[0]["status"] == TaskStatus.COMPLETED.value
    assert all(step["status"] == TaskStatus.CANCELED.value for step in plan[1:])


def test_cancel_incomplete_steps_noop_without_plan():
    store = TaskStore()
    store.create_task("t2", "prompt", {})

    # Should not raise or modify anything
    store.cancel_incomplete_steps("t2")

    task = store.get_task("t2")
    assert task.plan == []