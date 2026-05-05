import pytest

from orchestrator.services.planner import build_plan


def test_build_plan_single_robot_prefers_navigation():
    plan = build_plan("Отправь carter01 на склад А")
    assert len(plan) >= 3
    last = plan[-1]
    assert last.agent == "Navigation"
    assert last.meta["target_robots"] == ["carter01"]
    assert "submit_navigation_mission" in last.meta["tools"]
    assert "plan_route" not in last.meta["tools"]


def test_build_plan_multi_robot_prefers_swarm_and_routes():
    plan = build_plan("Организуй встречу carter01 и carter02")
    assert len(plan) >= 3
    last = plan[-1]
    assert last.agent == "SwarmCoordinator"
    assert set(last.meta["target_robots"]) == {"carter01", "carter02"}
    assert "dispatch_mission" in last.meta["tools"]
    assert "get_mission_status" in last.meta["tools"]


def test_build_plan_swarm_keyword_without_ids():
    plan = build_plan("Скоординируй рой роботов для осмотра склада")
    last = plan[-1]
    assert last.agent == "SwarmCoordinator"
    assert last.meta["target_robots"] == []
    assert "dispatch_mission" in last.meta["tools"]


def test_build_plan_splits_multiple_goals():
    plan = build_plan("Сначала отвези carter01 на склад, потом забери carter02 на базе")
    assert len(plan) >= 4
    exec_steps = plan[2:]
    assert len(exec_steps) == 2
    assert exec_steps[0].agent == "Navigation"
    assert exec_steps[1].agent in {"Navigation", "Swarm"}
    # ensure target robots extracted per goal
    targets = exec_steps[0].meta["target_robots"] + exec_steps[1].meta["target_robots"]
    assert set(targets) == {"carter01", "carter02"}
