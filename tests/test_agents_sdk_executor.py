from types import SimpleNamespace

import pytest

from orchestrator.services import agents_sdk
from orchestrator.services.plan_runner import HandoffResult
from orchestrator.services.planner import PlanStep
from orchestrator.services.streaming import StreamCollector
from orchestrator.services.tasks import TaskStore


@pytest.mark.asyncio
async def test_agents_sdk_executor_streams_and_uses_run_config(monkeypatch):
    """RunConfig/nest_handoff_history should be forwarded and stream events recorded."""

    # Force nested history for assertion
    monkeypatch.setenv("AGENTS_NEST_HANDOFF_HISTORY", "1")

    # Bypass real OpenAI client/model creation
    monkeypatch.setattr(agents_sdk, "_router_agent", lambda: object())
    monkeypatch.setattr(agents_sdk, "_build_agent", lambda name, mcp_configs=None: object())

    run_called: dict = {}

    class DummyResult:
        def __init__(self):
            self.final_output = "ok"

        async def stream_events(self):
            yield SimpleNamespace(type="run_item_stream_event", name="message_output_created", item=None)

        def final_output_as(self, cls):  # pragma: no cover - invoked for parsing
            return cls(category="general", reason="done", target_robots=[], confidence=0.9)

    def fake_run_streamed(agent, input, run_config=None):
        run_called["run_config"] = run_config
        return DummyResult()

    monkeypatch.setattr(agents_sdk, "Runner", SimpleNamespace(run_streamed=fake_run_streamed, run=None))

    sc = StreamCollector(task_store=TaskStore())
    executor = agents_sdk.AgentsSDKExecutor(stream_collector=sc)

    step = PlanStep(id=1, description="route request", agent="Router")
    result: HandoffResult = await executor.execute(task_id="t1", step=step, attempt=1)

    assert result.success is True
    assert "run_config" in run_called
    assert run_called["run_config"].nest_handoff_history is True

    payload = sc.as_payload("t1")
    assert payload["events"], "stream events should be recorded"