import pytest

from service.services.agents.events import EventType
from service.services.agents.subagents.image_generation import ImageGenerationAgent


class _Msg:
    def __init__(self, content: str):
        self.content = content


class _Choice:
    def __init__(self, content: str):
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content: str):
        self.choices = [_Choice(content)]


class _BrokenImagesClient:
    class _Images:
        async def generate(self, **kwargs):  # noqa: ANN003
            raise RuntimeError("image api unavailable")

    def __init__(self):
        self.images = self._Images()


@pytest.mark.asyncio
async def test_image_agent_falls_back_to_prompt_when_image_api_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    from service.services.agents import client as agents_client

    async def _fake_models() -> list[str]:
        return ["qwen-image", "mws-gpt-alpha"]

    async def _fake_chat_completion(**kwargs):  # noqa: ANN003
        return _Resp("### Prompt\nA cinematic portrait")

    monkeypatch.setattr(agents_client, "list_available_models", _fake_models)
    monkeypatch.setattr(agents_client, "get_openai_client", lambda: _BrokenImagesClient())
    monkeypatch.setattr(agents_client, "create_chat_completion", _fake_chat_completion)

    agent = ImageGenerationAgent(model_settings={})
    events = []
    async for event in agent.process("сгенерируй картинку космос", context=None):
        events.append(event)

    stream_chunks = [e for e in events if e.type == EventType.STREAM_CHUNK]
    assert stream_chunks, "Expected at least one stream chunk"

    combined_text = "\n".join(str(e.data or "") for e in stream_chunks)
    assert "готовый промпт" in combined_text.lower() or "промпт" in combined_text.lower()
    assert "cinematic portrait" in combined_text.lower()
