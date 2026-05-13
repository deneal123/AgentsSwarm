import json


def test_process_chat_message_core_publishes_agent_reply(monkeypatch):
    from service.infrastructure.messaging.tasks import process_chat_message_core

    class FakeRedis:
        def __init__(self):
            self.added = []

        def xadd(self, stream, mapping):
            self.added.append((stream, mapping))
            return "1-0"

    fake_redis = FakeRedis()

    class FakeChatAppService:
        async def post_message(self, thread_id, payload):
            return {
                "reply": "Here is your answer.",
                "thread_id": thread_id,
                "metadata": {},
            }

    class FakeInfra:
        redis_client = fake_redis

    class FakeServices:
        chat_application_service = FakeChatAppService()

    class FakeContainer:
        infra = FakeInfra()
        services = FakeServices()

    monkeypatch.setattr(
        "service.composition.state.get_current_container",
        lambda: FakeContainer(),
    )

    res = process_chat_message_core("T1", "m-1", "Hello", 1)

    assert res.get("reply") == "Here is your answer."

    agent_messages = [
        json.loads(m.get("data"))
        for s, m in fake_redis.added
        if s == "chat:T1:stream" and "data" in m
    ]
    assert any(msg.get("type") == "agent_reply" for msg in agent_messages), (
        f"Expected agent_reply in redis stream; got: {fake_redis.added}"
    )
