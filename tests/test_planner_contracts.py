import pytest

from orchestrator.services.planner import build_plan


def test_build_plan_single_robot_prefers_navigation():
    plan = build_plan("Отправь carter01 на склад А")
    assert len(plan) == 3
    assert plan[2].agent == "Navigation"
    assert plan[2].meta["target_robots"] == ["carter01"]
    assert "create_mission" in plan[2].meta["tools"]
    assert "plan_route" not in plan[2].meta["tools"]


def test_build_plan_multi_robot_prefers_swarm_and_routes():
    plan = build_plan("Организуй встречу carter01 и carter02")
    assert len(plan) == 3
    assert plan[2].agent == "Swarm"
    assert set(plan[2].meta["target_robots"]) == {"carter01", "carter02"}
    assert "plan_route" in plan[2].meta["tools"]
    assert "send_mission" in plan[2].meta["tools"]


def test_build_plan_swarm_keyword_without_ids():
    plan = build_plan("Скоординируй рой роботов для осмотра склада")
    assert plan[2].agent == "Swarm"
    assert plan[2].meta["target_robots"] == []
    assert "plan_route" in plan[2].meta["tools"]
