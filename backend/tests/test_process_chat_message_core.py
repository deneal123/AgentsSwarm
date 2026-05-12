import json
from types import SimpleNamespace

import service.infrastructure.messaging.tasks as tasks
from service.services.chat.domain.chat_contracts import ChatProcessingMetadata, ChatReplyResult


def test_process_chat_message_core_publishes_agent_reply(monkeypatch):
    published = []

    class FakeRedis:
        def xadd(self, stream, mapping):
            published.append((stream, {k: v for k, v in mapping.items()}))
            return "1-0"

    class FakeChatAppService:
        async def post_message(self, thread_id, payload):
            return {
                "reply": "ok",
                "thread_id": thread_id,
                "metadata": {},
            }

    class FakeInfra:
        redis_client = FakeRedis()

    class FakeServices:
        chat_application_service = FakeChatAppService()

    class FakeContainer:
        infra = FakeInfra()
        services = FakeServices()

    monkeypatch.setattr(
        "service.composition.state.get_current_container",
        lambda: FakeContainer(),
    )

    res = tasks.process_chat_message_core("thread-1", "msg-1", "hello", user_id=42)

    assert isinstance(res, dict)
    assert res.get("reply") == "ok"

    job_entries = [p for p in published if p[0].startswith("chat:thread-1:stream")]
    assert any(json.loads(e[1]["data"]).get("type") == "agent_reply" for e in job_entries)
