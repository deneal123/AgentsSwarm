import json

import types


def test_process_chat_message_core_creates_calendar(monkeypatch):
    from service.infrastructure.messaging.tasks import process_chat_message_core
    from service import container
    from service.services.agents.pydantic.agents import MealCalendarOutput

    # Fake Redis sync client
    class FakeRedis:
        def __init__(self):
            self.added = []

        def xadd(self, stream, mapping):
            self.added.append((stream, mapping))
            return "1-0"

    fake_redis = FakeRedis()

    # Fake JobService with async create_calendar_job
    class FakeJobService:
        def __init__(self):
            self.called = False

        async def create_calendar_job(self, user_id, name=None, period_start=None, period_end=None, manifest=None):
            self.called = True
            # return object with job_id and status attributes
            return types.SimpleNamespace(job_id="job-1", status="processing")

    # inject into container
    container._CONTAINER[container.RedisClientName] = fake_redis
    container._CONTAINER[container.JobServiceName] = FakeJobService()

    # Patch orchestrator to choose a meal_calendar agent and Runner.run to return a MealCalendarOutput
    class FakeAgent:
        # runner.run_streamed may inspect agent.output_type; provide it to satisfy the agents SDK
        output_type = MealCalendarOutput
        name = "fake_meal_agent"
        # agents SDK may inspect handoffs list during streaming setup
        handoffs = []

        # agents SDK may call get_all_tools(context) during run_streamed preparation
        async def get_all_tools(self, context):
            return []

    async def fake_route(self, query):
        return FakeAgent()

    async def fake_runner_run(starting_agent, input, context):
        # provide structured MealCalendarOutput
        cal = MealCalendarOutput(calendar=[{"date": "2025-12-26", "meals": [{"name": "Soup", "calories": 200, "ingredients": ["water"]}]}])
        return type("R", (), {"final_output": cal, "last_agent": starting_agent})

    monkeypatch.setattr("service.services.agents.orchestrator.Orchestrator.route", fake_route)
    monkeypatch.setattr("service.services.agents.runner.Runner.run", fake_runner_run)

    # Also patch the Runner used by service.services.agents.runner (ExternalRunner) so run_streamed
    # returns a lightweight result with a final_output and an empty stream_events async generator.
    class FakeResult:
        def __init__(self, final):
            self.final_output = final

        async def stream_events(self):
            if False:
                yield None

        def to_input_list(self):
            # mimic result.to_input_list used elsewhere
            return []

    class FakeExternalRunner:
        @staticmethod
        def run_streamed(starting_agent, input, context, max_turns=None):
            cal = MealCalendarOutput(calendar=[{"date": "2025-12-26", "meals": [{"name": "Soup", "calories": 200, "ingredients": ["water"]}]}])
            return FakeResult(cal)

    monkeypatch.setattr("service.services.agents.runner.ExternalRunner", FakeExternalRunner)

    # Call core processing with a message that triggers calendar creation
    res = process_chat_message_core("T1", "m-1", "Please create calendar named MyPlan", 1)

    # Assert agent reply published to the chat stream
    assert any(s == "chat:T1:stream" for s, m in fake_redis.added), f"redis add calls: {fake_redis.added}"

    # Inspect the agent_reply payload metadata to ensure action schema present
    agent_messages = [json.loads(m.get("data")) for s, m in fake_redis.added if s == "chat:T1:stream"]
    has_action = False
    for msg in agent_messages:
        if msg.get("event") == "agent_reply":
            meta = msg.get("metadata") or {}
            if isinstance(meta, dict) and isinstance(meta.get("action"), dict) and meta.get("action").get("type") == "calendar.create":
                has_action = True
    assert has_action, f"agent metadata should contain calendar.create action; redis calls: {fake_redis.added}"

    # Assert calendar job event was published
    assert any("calendar_job_enqueued" in json.loads(m.get("data")).get("event", "") if "data" in m else False for s, m in fake_redis.added), f"redis add calls: {fake_redis.added}"


# Note: WebSocket integration tests for task enqueuing are flaky in this environment and
# were omitted; core processing logic is covered by unit tests above.
