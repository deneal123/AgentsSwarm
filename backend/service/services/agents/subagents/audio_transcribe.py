"""Audio transcription-focused sub-agent."""

from __future__ import annotations

import logging
import re
from typing import AsyncGenerator

from service.services.agents.domain.events import AgentEvent, EventType
from service.services.agents.schemas.agents import UserContext
from service.services.agents.subagents.base import BaseSubAgent
from service.services.agents.subagents.utils import pick_text_model

logger = logging.getLogger(__name__)

_FILE_CONTEXT_MARKER = "## Контекст из загруженного файла:"


def _split_effective_input(text: str) -> tuple[str, str]:
    value = str(text or "")
    if _FILE_CONTEXT_MARKER not in value:
        return value.strip(), ""

    user_part, file_part = value.split(_FILE_CONTEXT_MARKER, 1)
    return user_part.strip(), file_part.strip()


def _normalize_transcript(text: str, max_chars: int = 18000) -> str:
    transcript = str(text or "").strip()
    transcript = re.sub(r"\n{3,}", "\n\n", transcript)
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars].rstrip() + "\n\n...[транскрипт обрезан]"
    return transcript


def _looks_like_transcription_failure(text: str) -> bool:
    low = str(text or "").lower()
    markers = (
        "транскрипция недоступна",
        "аудио загружено, но транскрипция недоступна",
        "аудио файл:",
        "аудио не распознано",
    )
    return any(marker in low for marker in markers)


class AudioTranscriptionAgent(BaseSubAgent):
    """Specialized agent for stable audio speech-to-text workflows."""

    def __init__(self, model_settings: dict):
        super().__init__(
            name="audio_transcribe",
            instructions=(
                "Обрабатывай аудио-запросы стабильно: сначала явно показывай распознанный текст, "
                "после этого выполняй дополнительную задачу пользователя (суммаризация/перевод/выжимка), "
                "если она была запрошена."
            ),
            model_settings=model_settings,
        )

    async def process(self, user_input: str, context: UserContext) -> AsyncGenerator[AgentEvent, None]:
        yield self.start_event("Запускаю обработку аудио и распознавание речи")

        safety = await self.evaluate_input_safety(user_input)
        if safety["sensitive"]:
            yield AgentEvent(
                type=EventType.STATUS_UPDATE,
                agent_name=self.name,
                data="⚠️ Чувствительная тема: вывод ограничен безопасным форматом.",
                metadata=safety["meta"],
            )
        if safety["blocked"]:
            yield AgentEvent(
                type=EventType.ERROR,
                agent_name=self.name,
                data=safety["message"],
                metadata=safety["meta"],
            )
            yield self.complete_event("Обработка аудио остановлена guardrails")
            return

        user_task, file_context = _split_effective_input(user_input)
        transcript = _normalize_transcript(file_context)

        if not transcript:
            yield self.error_event(
                "Не найден аудиоконтекст для распознавания. Прикрепите аудиофайл и повторите запрос."
            )
            yield self.complete_event("Обработка аудио завершена без транскрипта")
            return

        if _looks_like_transcription_failure(transcript):
            yield self.error_event(
                "Не удалось распознать речь в аудиофайле. Попробуйте другой формат (wav/mp3/m4a) "
                "или более качественную запись."
            )
            yield self.complete_event("Обработка аудио завершена с ошибкой распознавания")
            return

        yield AgentEvent(
            type=EventType.TOOL_CALL_COMPLETE,
            agent_name=self.name,
            data=f"Распознано символов: {len(transcript)}",
            metadata={"transcript_chars": len(transcript)},
        )

        base_output = f"### Распознанный текст\n\n{transcript}"

        normalized_task = (user_task or "").strip().lower()
        pure_transcribe_request = any(
            marker in normalized_task
            for marker in ("распознай", "транскриб", "speech to text", "stt", "переведи в текст")
        ) and len(normalized_task) < 180

        if not normalized_task or pure_transcribe_request:
            async for chunk_event in self.stream_text_chunks(base_output):
                yield chunk_event
            yield self.complete_event("Распознавание аудио завершено")
            return

        try:
            from service.services.agents.client import create_chat_completion, list_available_models

            models = await list_available_models()
            model = pick_text_model(models)
            if not model:
                async for chunk_event in self.stream_text_chunks(base_output):
                    yield chunk_event
                yield self.complete_event("Распознавание аудио завершено")
                return

            resp = await create_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты помощник по обработке аудио-транскриптов. "
                            "Всегда сначала приведи блок '### Распознанный текст' с исходным текстом, "
                            "а затем выполни задачу пользователя по этому транскрипту. "
                            "Не выдумывай фразы, которых нет в транскрипте."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Запрос пользователя:\n{user_task}\n\n"
                            f"Транскрипт:\n{transcript}"
                        ),
                    },
                ],
                model=model,
                temperature=0.2,
                max_tokens=1400,
            )
            reply = getattr(resp.choices[0].message, "content", "") or ""
            if not reply.strip():
                reply = base_output

            async for chunk_event in self.stream_text_chunks(reply):
                yield chunk_event
        except Exception as exc:
            logger.exception("Audio transcription sub-agent failed")
            async for chunk_event in self.stream_text_chunks(
                f"{base_output}\n\n---\n\n⚠️ Дополнительная обработка не выполнена: {exc}"
            ):
                yield chunk_event

        yield self.complete_event("Обработка аудио завершена")
