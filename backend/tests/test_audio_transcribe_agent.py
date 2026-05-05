import pytest

from service.agents.events import EventType
from service.agents.subagents.audio_transcribe import AudioTranscriptionAgent


@pytest.mark.asyncio
async def test_audio_transcribe_agent_returns_transcript_block(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = AudioTranscriptionAgent(model_settings={})

    async def _safe_guardrails(_text: str):
        return {
            "blocked": False,
            "sensitive": False,
            "meta": {},
            "message": None,
        }

    monkeypatch.setattr(agent, "evaluate_input_safety", _safe_guardrails)

    user_input = (
        "Распознай этот аудиофайл\n\n"
        "## Контекст из загруженного файла:\n"
        "Привет! Это тестовая запись голоса."
    )

    events = []
    async for event in agent.process(user_input, context=None):
        events.append(event)

    chunks = [e for e in events if e.type == EventType.STREAM_CHUNK]
    assert chunks

    merged = "\n".join(str(e.data or "") for e in chunks)
    assert "Распознанный текст" in merged
    assert "тестовая запись голоса" in merged


@pytest.mark.asyncio
async def test_audio_transcribe_agent_returns_error_when_file_context_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = AudioTranscriptionAgent(model_settings={})

    async def _safe_guardrails(_text: str):
        return {
            "blocked": False,
            "sensitive": False,
            "meta": {},
            "message": None,
        }

    monkeypatch.setattr(agent, "evaluate_input_safety", _safe_guardrails)

    events = []
    async for event in agent.process("распознай аудио", context=None):
        events.append(event)

    errors = [e for e in events if e.type == EventType.ERROR]
    assert errors
    assert "Не найден аудиоконтекст" in str(errors[0].data or "")
