import json
from types import SimpleNamespace

import service.infrastructure.messaging.tasks as tasks
from service.chat.domain.chat_contracts import ChatProcessingMetadata, ChatReplyResult


def test_process_chat_message_core_publishes_agent_reply(monkeypatch):
    published = []

    class FakeRedis:
        def xadd(self, stream, mapping):
            published.append((stream, {k: v for k, v in mapping.items()}))
            return "1-0"

    class FakeJobService:
        async def create_calendar_job(self, user_id: str, name: str | None = None, period_start=None, period_end=None, manifest=None):
            return SimpleNamespace(job_id="job-123", status="queued")

    class FakeChatService:
        def __init__(self, *args, **kwargs):
            pass

        async def post_message(self, context):
            return ChatReplyResult(
                reply="ok",
                thread_id=context.thread_id,
                metadata=ChatProcessingMetadata(data={"action": {"type": "calendar.create", "payload": {"name": "testcal"}}}),
            )

    # patch ChatService import used inside the function
    import service.chat.domain.chat_service as chat_mod

    monkeypatch.setattr(chat_mod, "ChatService", FakeChatService)

    # patch container.get to return fake redis and fake job service
    import service.container as container

    def fake_get(name):
        if name == container.RedisClientName:
            return FakeRedis()
        if name == container.JobServiceName:
            return FakeJobService()
        raise KeyError(name)

    monkeypatch.setattr(container, "get", fake_get)

    # Call process_chat_message_core (synchronous wrapper will run async post_message)
    res = tasks.process_chat_message_core("thread-1", "msg-1", "hello", user_id=42)

    # Assert reply returned
    assert isinstance(res, dict)
    assert res.get("reply") == "ok"

    # Ensure published includes agent_reply in the current event contract (`type`, not legacy `event`).
    job_entries = [p for p in published if p[0].startswith("chat:thread-1:stream")]
    assert any(json.loads(e[1]["data"]).get("type") == "agent_reply" for e in job_entries)
