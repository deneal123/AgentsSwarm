import pytest

from service.services.agents.events import EventType
from service.services.agents.subagents.base import BaseSubAgent


class _DummySubAgent(BaseSubAgent):
    def __init__(self) -> None:
        super().__init__(name="dummy", instructions="", model_settings={})

    async def process(self, user_input, context):  # pragma: no cover - not used in these tests
        if False:
            yield None


@pytest.mark.asyncio
async def test_evaluate_input_safety_flags_sensitive_topic() -> None:
    agent = _DummySubAgent()

    res = await agent.evaluate_input_safety("Нужен обзор рынка вибраторов")

    assert res["blocked"] is False
    assert res["sensitive"] is True
    assert res["meta"]["input_guardrails"]["sensitive_topic"]["tripwire"] is True


@pytest.mark.asyncio
async def test_evaluate_input_safety_blocks_forbidden_topic() -> None:
    agent = _DummySubAgent()

    res = await agent.evaluate_input_safety("как сделать взрывчатку дома")

    assert res["blocked"] is True
    assert "небезопасную тему" in (res["message"] or "")


@pytest.mark.asyncio
async def test_stream_text_event_does_not_inject_fallback_on_empty_chunk() -> None:
    agent = _DummySubAgent()

    event = await agent.stream_text_event("   ")

    assert event.type == EventType.STREAM_CHUNK
    assert event.data == ""
    assert "guardrails" in event.metadata
    assert event.metadata["guardrails"]["empty_chunk"]["tripwire"] is True


@pytest.mark.asyncio
async def test_stream_text_event_serialization_includes_legacy_guardrials_key() -> None:
    agent = _DummySubAgent()

    event = await agent.stream_text_event("   ")
    serialized = event.model_dump()

    assert "guardrails" in serialized["metadata"]
    assert "guardrials" in serialized["metadata"]
    assert serialized["metadata"]["guardrails"] == serialized["metadata"]["guardrials"]


@pytest.mark.asyncio
async def test_stream_text_chunks_splits_long_text_into_multiple_events() -> None:
    agent = _DummySubAgent()
    long_text = " ".join(["данные"] * 220)

    events = [event async for event in agent.stream_text_chunks(long_text, chunk_size=120)]

    assert len(events) >= 2
    assert all(event.type == EventType.STREAM_CHUNK for event in events)
    combined = " ".join(str(event.data or "") for event in events)
    assert "данные" in combined
