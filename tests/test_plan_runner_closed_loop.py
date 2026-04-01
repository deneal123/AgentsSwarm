import pytest

from orchestrator.services.plan_runner import AgentHandoffExecutor, HandoffResult, PlanRunner
from orchestrator.services.planner import build_plan
from orchestrator.services.streaming import StreamCollector
from orchestrator.services.tasks import TaskStatus, TaskStore


class ControlledExecutor(AgentHandoffExecutor):
    def __init__(self, outcomes: dict[int, list[bool | HandoffResult]]):
        self._outcomes = {k: list(v) for k, v in outcomes.items()}

    async def execute(self, task_id, step, attempt):
        seq = self._outcomes.get(step.id, [])
        if seq:
            choice = seq.pop(0)
        else:
            choice = True

        if isinstance(choice, HandoffResult):
            return choice

        return HandoffResult(
            success=bool(choice),
            message="ok" if choice else "fail",
            user_message=None if choice else "Шаг не выполнен",
            retryable=True,
        )


@pytest.mark.asyncio
async def test_runner_retries_until_success_with_handoff_stream():
    task_store = TaskStore()
    sc = StreamCollector(task_store)
    task_id = "task-retry"
    plan = build_plan("Отправь робота к точке")

    task_store.create_task(task_id, "Отправь робота к точке", {})
    task_store.set_plan(task_id, [s.as_dict() for s in plan])
    task_store.update_status(task_id, TaskStatus.RUNNING)

    executor = ControlledExecutor({3: [False, True]})
    runner = PlanRunner(task_store, sc, agent_executor=executor, max_attempts=3, retry_delay=0)

    outcome = await runner.run(task_id, plan)

    assert outcome == TaskStatus.COMPLETED
    task = task_store.get_task(task_id)
    assert task is not None
    assert all(step["status"] == TaskStatus.COMPLETED.value for step in task.plan)

    messages = [ev.message for ev in sc.get_events(task_id)]
    assert any("Повтор шага" in msg for msg in messages)
    assert any("Plan step 3 completed" in msg for msg in messages)
    assert any("Handoff to" in msg for msg in messages)


@pytest.mark.asyncio
async def test_runner_marks_task_failed_after_exhausting_retries():
    task_store = TaskStore()
    sc = StreamCollector(task_store)
    task_id = "task-fail"
    plan = build_plan("Выполни сложную миссию")

    task_store.create_task(task_id, "Выполни сложную миссию", {})
    task_store.set_plan(task_id, [s.as_dict() for s in plan])
    task_store.update_status(task_id, TaskStatus.RUNNING)

    executor = ControlledExecutor({3: [False, False]})
    runner = PlanRunner(task_store, sc, agent_executor=executor, max_attempts=2, retry_delay=0)

    outcome = await runner.run(task_id, plan)

    assert outcome == TaskStatus.FAILED
    task = task_store.get_task(task_id)
    assert task is not None
    assert task.status == TaskStatus.FAILED

    status_by_id = {step["id"]: step["status"] for step in task.plan}
    assert status_by_id[3] == TaskStatus.FAILED.value

    events = sc.get_events(task_id)
    user_events = [ev for ev in events if ev.meta.get("user_facing")]
    assert user_events
    assert any("останов" in ev.message.lower() or "шаг" in ev.message.lower() for ev in user_events)
