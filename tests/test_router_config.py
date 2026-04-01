from orchestrator.agents.router import get_router_config


def test_router_contains_fallback_and_handoffs():
    cfg = get_router_config()
    assert cfg["name"] == "Router"
    handoffs = cfg["handoffs"]
    names = {h["name"] for h in handoffs}
    assert {"RobotInfo", "Navigation", "SwarmCoordinator", "General"}.issubset(names)


def test_router_has_smoke_prompts_for_routing():
    cfg = get_router_config()
    tests = cfg.get("router_tests", {})
    assert "robot_info" in tests and tests["robot_info"]
    assert "navigation" in tests and tests["navigation"]
    assert "swarm_coord" in tests and tests["swarm_coord"]
    assert "general" in tests and tests["general"]
