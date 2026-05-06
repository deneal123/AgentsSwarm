import pytest
from unittest.mock import AsyncMock, patch

from orchestrator.services.planner import build_plan
from orchestrator.services import planner as planner_mod


def _make_goal(description: str, agent: str, robots: list[str] = []):
    from orchestrator.services.planner import _GoalItem
    return _GoalItem(description=description, agent=agent, target_robots=robots)


@pytest.mark.asyncio
async def test_build_plan_single_robot_prefers_navigation():
    goals = [_make_goal("Отправь carter01 на склад А", "Navigation", ["carter01"])]
    with patch.object(planner_mod, "_build_plan_llm", AsyncMock(return_value=goals)):
        plan = await build_plan("Отправь carter01 на склад А")
    assert len(plan) >= 3
    last = plan[-1]
    assert last.agent == "Navigation"
    assert last.meta["target_robots"] == ["carter01"]
    assert "submit_navigation_mission" in last.meta["tools"]
    assert "plan_route" not in last.meta["tools"]


@pytest.mark.asyncio
async def test_build_plan_multi_robot_prefers_swarm_and_routes():
    goals = [_make_goal("Организуй встречу carter01 и carter02", "SwarmCoordinator", ["carter01", "carter02"])]
    with patch.object(planner_mod, "_build_plan_llm", AsyncMock(return_value=goals)):
        plan = await build_plan("Организуй встречу carter01 и carter02")
    assert len(plan) >= 3
    last = plan[-1]
    assert last.agent == "SwarmCoordinator"
    assert set(last.meta["target_robots"]) == {"carter01", "carter02"}
    assert "dispatch_mission" in last.meta["tools"]
    assert "get_mission_status" in last.meta["tools"]


@pytest.mark.asyncio
async def test_build_plan_swarm_keyword_without_ids():
    goals = [_make_goal("Скоординируй рой роботов для осмотра склада", "SwarmCoordinator", [])]
    with patch.object(planner_mod, "_build_plan_llm", AsyncMock(return_value=goals)):
        plan = await build_plan("Скоординируй рой роботов для осмотра склада")
    last = plan[-1]
    assert last.agent == "SwarmCoordinator"
    assert last.meta["target_robots"] == []
    assert "dispatch_mission" in last.meta["tools"]


@pytest.mark.asyncio
async def test_build_plan_splits_multiple_goals():
    goals = [
        _make_goal("Отвези carter01 на склад", "Navigation", ["carter01"]),
        _make_goal("Забери carter02 на базе", "Navigation", ["carter02"]),
    ]
    with patch.object(planner_mod, "_build_plan_llm", AsyncMock(return_value=goals)):
        plan = await build_plan("Сначала отвези carter01 на склад, потом забери carter02 на базе")
    assert len(plan) >= 4
    exec_steps = [s for s in plan if s.agent in {"Navigation", "SwarmCoordinator"}]
    assert len(exec_steps) == 2
    assert exec_steps[0].agent == "Navigation"
    targets = exec_steps[0].meta["target_robots"] + exec_steps[1].meta["target_robots"]
    assert set(targets) == {"carter01", "carter02"}
