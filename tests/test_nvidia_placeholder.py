from nvidia_isaac_simulation import run_simulation_placeholder

def test_placeholder_returns_message():
    assert "ISAAC" in run_simulation_placeholder()
