from types import SimpleNamespace

from service.services.agents.base_agent import SimpleStreamingAgent


def test_extract_text_from_sdk_event_supports_responses_delta_shape() -> None:
    event = SimpleNamespace(
        type="raw_response_event",
        data=SimpleNamespace(type="response.output_text.delta", delta="Привет"),
    )

    out = SimpleStreamingAgent._extract_text_from_sdk_event(event)

    assert out == "Привет"


def test_extract_text_from_sdk_event_supports_message_output_item_shape() -> None:
    content_item = SimpleNamespace(text="Текст из item.content")
    raw = SimpleNamespace(item=SimpleNamespace(content=[content_item]))
    event = SimpleNamespace(type="raw_response_event", data=raw)

    out = SimpleStreamingAgent._extract_text_from_sdk_event(event)

    assert out == "Текст из item.content"


def test_split_text_chunks_produces_multiple_chunks_for_long_text() -> None:
    text = " ".join(["chunk"] * 180)

    chunks = SimpleStreamingAgent._split_text_chunks(text, chunk_size=100)

    assert len(chunks) >= 2
    assert all(isinstance(c, str) and c for c in chunks)
    assert "chunk" in " ".join(chunks)
