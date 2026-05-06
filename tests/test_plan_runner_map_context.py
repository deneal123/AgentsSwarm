"""Tests for PlanRunner map context injection between MapAnalyst and Navigation steps."""

from __future__ import annotations

import pytest
from dataclasses import dataclass
from typing import List

from orchestrator.services.plan_runner import AgentHandoffExecutor, HandoffResult, PlanRunner
from orchestrator.services.planner import PlanStep
from orchestrator.services.streaming import StreamCollector, StreamEvent
from orchestrator.services.tasks import TaskStatus, TaskStore


# ── helpers ──────────────────────────────────────────────────────────────────

_MAP_CONTEXT = (
    "=== MAP ANALYSIS RESULT ===\n"
    "TARGET: x=2.4, y=1.8\n"
    "BEST ROUTE: optimal\n"
    "WAYPOINTS: [(0.5, 0.3), (2.4, 1.8)]\n"
    "==========================="
)


def _make_store() -> TaskStore:
    store = TaskStore()
    store.create_task("t1", "test prompt", session_data={})
    return store


def _make_collector() -> StreamCollector:
    return StreamCollector()


def _make_step(id: int, agent: str, description: str = "") -> PlanStep:
    return PlanStep(
        id=id,
        description=description or f"Step {id}",
        agent=agent,
        meta={"depends_on": [], "tools": []},
    )


def _set_plan_from_steps(store: TaskStore, task_id: str, steps: list[PlanStep]) -> None:
    store.set_plan(task_id, [s.as_dict() for s in steps])


class RecordingExecutor:
    """Executor that records what description/meta each step had when executed."""

    def __init__(self, results: dict[int, HandoffResult]):
        self._results = results
        self.executed: list[PlanStep] = []

    async def execute(self, task_id: str, step: PlanStep, attempt: int) -> HandoffResult:
        import copy
        self.executed.append(copy.deepcopy(step))
        return self._results.get(step.id, HandoffResult(success=True, message=""))


def _runner(store: TaskStore, collector: StreamCollector, executor: AgentHandoffExecutor) -> PlanRunner:
    return PlanRunner(
        task_store=store,
        stream_collector=collector,
        agent_executor=executor,
    )


# ── context injection ─────────────────────────────────────────────────────────

class TestMapContextInjection:
    @pytest.mark.asyncio
    async def test_map_context_injected_into_navigation_description(self):
        store = _make_store()
        collector = _make_collector()

        plan = [
            _make_step(1, "Router"),
            _make_step(2, "RobotInfo"),
            _make_step(3, "MapAnalyst"),
            _make_step(4, "Navigation", "Move carter01 to center"),
        ]
        _set_plan_from_steps(store, "t1", plan)

        executor = RecordingExecutor({
            1: HandoffResult(success=True, message="routed"),
            2: HandoffResult(success=True, message="fleet ok"),
            3: HandoffResult(success=True, message=_MAP_CONTEXT),
            4: HandoffResult(success=True, message="mission submitted"),
        })

        store.update_status("t1", TaskStatus.RUNNING)
        runner = _runner(store, collector, executor)
        outcome = await runner.run("t1", plan)

        assert outcome == TaskStatus.COMPLETED
        nav_step = next(s for s in executor.executed if s.agent == "Navigation")
        assert _MAP_CONTEXT in nav_step.description

    @pytest.mark.asyncio
    async def test_map_context_injected_into_step_meta(self):
        store = _make_store()
        collector = _make_collector()

        plan = [
            _make_step(1, "Router"),
            _make_step(2, "RobotInfo"),
            _make_step(3, "MapAnalyst"),
            _make_step(4, "Navigation"),
        ]

        executor = RecordingExecutor({
            1: HandoffResult(success=True, message=""),
            2: HandoffResult(success=True, message=""),
            3: HandoffResult(success=True, message=_MAP_CONTEXT),
            4: HandoffResult(success=True, message=""),
        })
        _set_plan_from_steps(store, "t1", plan)

        store.update_status("t1", TaskStatus.RUNNING)
        await _runner(store, collector, executor).run("t1", plan)

        nav_step = next(s for s in executor.executed if s.agent == "Navigation")
        assert nav_step.meta.get("map_context") == _MAP_CONTEXT

    @pytest.mark.asyncio
    async def test_swarm_coordinator_also_gets_map_context(self):
        store = _make_store()
        collector = _make_collector()

        plan = [
            _make_step(1, "Router"),
            _make_step(2, "RobotInfo"),
            _make_step(3, "MapAnalyst"),
            _make_step(4, "SwarmCoordinator"),
        ]

        _set_plan_from_steps(store, "t1", plan)
        executor = RecordingExecutor({
            1: HandoffResult(success=True, message=""),
            2: HandoffResult(success=True, message=""),
            3: HandoffResult(success=True, message=_MAP_CONTEXT),
            4: HandoffResult(success=True, message=""),
        })

        store.update_status("t1", TaskStatus.RUNNING)
        await _runner(store, collector, executor).run("t1", plan)

        swarm_step = next(s for s in executor.executed if s.agent == "SwarmCoordinator")
        assert _MAP_CONTEXT in swarm_step.description

    @pytest.mark.asyncio
    async def test_empty_map_context_does_not_inject(self):
        store = _make_store()
        collector = _make_collector()

        original_description = "Move carter01 to center"
        plan = [
            _make_step(1, "Router"),
            _make_step(2, "RobotInfo"),
            _make_step(3, "MapAnalyst"),
            _make_step(4, "Navigation", original_description),
        ]
        _set_plan_from_steps(store, "t1", plan)

        executor = RecordingExecutor({
            1: HandoffResult(success=True, message=""),
            2: HandoffResult(success=True, message=""),
            3: HandoffResult(success=True, message=""),   # empty context
            4: HandoffResult(success=True, message=""),
        })

        store.update_status("t1", TaskStatus.RUNNING)
        await _runner(store, collector, executor).run("t1", plan)

        nav_step = next(s for s in executor.executed if s.agent == "Navigation")
        assert nav_step.description == original_description
        assert "map_context" not in nav_step.meta

    @pytest.mark.asyncio
    async def test_non_navigation_steps_do_not_get_map_context(self):
        store = _make_store()
        collector = _make_collector()

        plan = [
            _make_step(1, "Router"),
            _make_step(2, "RobotInfo"),
            _make_step(3, "MapAnalyst"),
            _make_step(4, "General"),
        ]
        _set_plan_from_steps(store, "t1", plan)

        executor = RecordingExecutor({
            1: HandoffResult(success=True, message=""),
            2: HandoffResult(success=True, message=""),
            3: HandoffResult(success=True, message=_MAP_CONTEXT),
            4: HandoffResult(success=True, message=""),
        })

        store.update_status("t1", TaskStatus.RUNNING)
        await _runner(store, collector, executor).run("t1", plan)

        general_step = next(s for s in executor.executed if s.agent == "General")
        assert "map_context" not in general_step.meta
        assert _MAP_CONTEXT not in general_step.description

    @pytest.mark.asyncio
    async def test_context_injected_into_all_subsequent_navigation_steps(self):
        """Multiple navigation steps all receive the context."""
        store = _make_store()
        collector = _make_collector()

        plan = [
            _make_step(1, "Router"),
            _make_step(2, "RobotInfo"),
            _make_step(3, "MapAnalyst"),
            _make_step(4, "Navigation", "Move carter01"),
            _make_step(5, "Navigation", "Move carter02"),
        ]
        _set_plan_from_steps(store, "t1", plan)

        executor = RecordingExecutor({
            1: HandoffResult(success=True, message=""),
            2: HandoffResult(success=True, message=""),
            3: HandoffResult(success=True, message=_MAP_CONTEXT),
            4: HandoffResult(success=True, message=""),
            5: HandoffResult(success=True, message=""),
        })

        store.update_status("t1", TaskStatus.RUNNING)
        await _runner(store, collector, executor).run("t1", plan)

        nav_steps = [s for s in executor.executed if s.agent == "Navigation"]
        assert len(nav_steps) == 2
        for step in nav_steps:
            assert _MAP_CONTEXT in step.description


# ── plan without MapAnalyst ───────────────────────────────────────────────────

class TestPlanWithoutMapAnalyst:
    @pytest.mark.asyncio
    async def test_plan_without_map_analyst_runs_normally(self):
        store = _make_store()
        collector = _make_collector()

        plan = [
            _make_step(1, "Router"),
            _make_step(2, "RobotInfo"),
            _make_step(3, "RobotInfo", "Get fleet status"),
        ]
        _set_plan_from_steps(store, "t1", plan)

        executor = RecordingExecutor({
            1: HandoffResult(success=True, message=""),
            2: HandoffResult(success=True, message=""),
            3: HandoffResult(success=True, message="fleet: 3 robots"),
        })

        store.update_status("t1", TaskStatus.RUNNING)
        outcome = await _runner(store, collector, executor).run("t1", plan)

        assert outcome == TaskStatus.COMPLETED
        assert len(executor.executed) == 3


# ── execute_step return type ──────────────────────────────────────────────────

class TestExecuteStepReturnType:
    @pytest.mark.asyncio
    async def test_execute_step_returns_tuple_on_success(self):
        store = _make_store()
        collector = _make_collector()

        step = _make_step(1, "Router")
        _set_plan_from_steps(store, "t1", [step])
        executor = RecordingExecutor({1: HandoffResult(success=True, message="done")})

        store.update_status("t1", TaskStatus.RUNNING)
        runner = _runner(store, collector, executor)
        status, msg = await runner._execute_step("t1", step)

        assert status is None
        assert msg == "done"

    @pytest.mark.asyncio
    async def test_execute_step_returns_none_message_on_failure(self):
        store = _make_store()
        collector = _make_collector()

        step = _make_step(1, "Router")
        _set_plan_from_steps(store, "t1", [step])
        executor = RecordingExecutor({
            1: HandoffResult(success=False, message="error", retryable=False)
        })

        store.update_status("t1", TaskStatus.RUNNING)
        runner = _runner(store, collector, executor)
        status, msg = await runner._execute_step("t1", step)

        assert status == TaskStatus.FAILED
        assert msg is None
