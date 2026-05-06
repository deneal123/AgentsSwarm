"""Tests for MapAnalyst step insertion in build_plan."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch


def _make_goal(description: str, agent: str, robots: list[str] = []):
    from orchestrator.services.planner import _GoalItem
    return _GoalItem(description=description, agent=agent, target_robots=robots)


async def _build(prompt: str, goals):
    """Patch LLM to return controlled goals and call build_plan."""
    from orchestrator.services import planner

    with patch.object(planner, "_build_plan_llm", AsyncMock(return_value=goals)):
        return await planner.build_plan(prompt)


# ── MapAnalyst step presence ──────────────────────────────────────────────────

class TestMapAnalystStepInsertion:
    @pytest.mark.asyncio
    async def test_navigation_goal_inserts_map_analyst_step(self):
        goals = [_make_goal("Move carter01 to center", "Navigation", ["carter01"])]
        plan = await _build("Move carter01 to center", goals)

        agents = [s.agent for s in plan]
        assert "MapAnalyst" in agents

    @pytest.mark.asyncio
    async def test_swarm_goal_inserts_map_analyst_step(self):
        goals = [_make_goal("Send all robots to zone A", "SwarmCoordinator", [])]
        plan = await _build("Send all robots to zone A", goals)

        agents = [s.agent for s in plan]
        assert "MapAnalyst" in agents

    @pytest.mark.asyncio
    async def test_robot_info_goal_has_no_map_analyst_step(self):
        goals = [_make_goal("Get fleet status", "RobotInfo", [])]
        plan = await _build("Get fleet status", goals)

        agents = [s.agent for s in plan]
        assert "MapAnalyst" not in agents

    @pytest.mark.asyncio
    async def test_general_goal_has_no_map_analyst_step(self):
        goals = [_make_goal("Hello", "General", [])]
        plan = await _build("Hello", goals)

        agents = [s.agent for s in plan]
        assert "MapAnalyst" not in agents

    @pytest.mark.asyncio
    async def test_mixed_goals_inserts_map_analyst_when_any_navigation(self):
        goals = [
            _make_goal("Get fleet status", "RobotInfo", []),
            _make_goal("Move carter01", "Navigation", ["carter01"]),
        ]
        plan = await _build("Get fleet status then move carter01", goals)

        agents = [s.agent for s in plan]
        assert "MapAnalyst" in agents


# ── MapAnalyst step position and id ──────────────────────────────────────────

class TestMapAnalystStepPosition:
    @pytest.mark.asyncio
    async def test_map_analyst_step_is_id_3(self):
        goals = [_make_goal("Move carter01", "Navigation", ["carter01"])]
        plan = await _build("Move carter01", goals)

        map_step = next(s for s in plan if s.agent == "MapAnalyst")
        assert map_step.id == 3

    @pytest.mark.asyncio
    async def test_map_analyst_step_comes_after_robot_info(self):
        goals = [_make_goal("Move carter01", "Navigation", ["carter01"])]
        plan = await _build("Move carter01", goals)

        agents = [s.agent for s in plan]
        robot_info_idx = agents.index("RobotInfo")
        map_analyst_idx = agents.index("MapAnalyst")
        assert map_analyst_idx > robot_info_idx

    @pytest.mark.asyncio
    async def test_execution_steps_start_at_id_4_with_map_analyst(self):
        goals = [_make_goal("Move carter01", "Navigation", ["carter01"])]
        plan = await _build("Move carter01", goals)

        exec_step = next(s for s in plan if s.agent == "Navigation")
        assert exec_step.id == 4

    @pytest.mark.asyncio
    async def test_execution_steps_start_at_id_3_without_map_analyst(self):
        goals = [_make_goal("Get status", "RobotInfo", [])]
        plan = await _build("Get status", goals)

        exec_step = next(s for s in plan if s.agent == "RobotInfo" and s.id >= 3)
        assert exec_step.id == 3


# ── MapAnalyst step meta ──────────────────────────────────────────────────────

class TestMapAnalystStepMeta:
    @pytest.mark.asyncio
    async def test_map_analyst_meta_contains_task_description(self):
        goals = [_make_goal("Move carter01 to the center", "Navigation", ["carter01"])]
        plan = await _build("Move carter01 to the center", goals)

        map_step = next(s for s in plan if s.agent == "MapAnalyst")
        assert "task_description" in map_step.meta
        assert "Move carter01 to the center" in map_step.meta["task_description"]

    @pytest.mark.asyncio
    async def test_map_analyst_meta_joins_multiple_nav_goals(self):
        goals = [
            _make_goal("Move carter01 to A", "Navigation", ["carter01"]),
            _make_goal("Move carter02 to B", "Navigation", ["carter02"]),
        ]
        plan = await _build("Move both robots", goals)

        map_step = next(s for s in plan if s.agent == "MapAnalyst")
        task_desc = map_step.meta["task_description"]
        assert "Move carter01 to A" in task_desc
        assert "Move carter02 to B" in task_desc

    @pytest.mark.asyncio
    async def test_execution_steps_depend_on_map_analyst(self):
        goals = [_make_goal("Move carter01", "Navigation", ["carter01"])]
        plan = await _build("Move carter01", goals)

        exec_step = next(s for s in plan if s.agent == "Navigation")
        assert 3 in exec_step.meta.get("depends_on", [])

    @pytest.mark.asyncio
    async def test_execution_steps_without_map_analyst_depend_on_1_and_2(self):
        goals = [_make_goal("Get status", "RobotInfo", [])]
        plan = await _build("Get status", goals)

        exec_step = next(s for s in plan if s.agent == "RobotInfo" and s.id >= 3)
        depends = exec_step.meta.get("depends_on", [])
        assert 1 in depends
        assert 2 in depends
        assert 3 not in depends


# ── Fixed plan structure ──────────────────────────────────────────────────────

class TestPlanStructure:
    @pytest.mark.asyncio
    async def test_plan_always_starts_with_router_and_robot_info(self):
        goals = [_make_goal("Move carter01", "Navigation", ["carter01"])]
        plan = await _build("Move carter01", goals)

        assert plan[0].agent == "Router"
        assert plan[0].id == 1
        assert plan[1].agent == "RobotInfo"
        assert plan[1].id == 2

    @pytest.mark.asyncio
    async def test_heuristic_fallback_still_inserts_map_analyst(self):
        """When LLM returns None, heuristic fallback is used — Navigation goals still get MapAnalyst."""
        from orchestrator.services import planner

        with patch.object(planner, "_build_plan_llm", AsyncMock(return_value=None)):
            plan = await planner.build_plan("Move robot carter01 to point A")

        agents = [s.agent for s in plan]
        # Heuristic detects 'carter01' → Navigation → MapAnalyst should be inserted
        assert "Navigation" in agents or "SwarmCoordinator" in agents
        if "Navigation" in agents or "SwarmCoordinator" in agents:
            assert "MapAnalyst" in agents
