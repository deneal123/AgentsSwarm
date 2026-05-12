"""PPTX generation sub-agent."""

import base64
import logging
from typing import AsyncGenerator

from service.services.agents.domain.events import AgentEvent, EventType
from service.services.agents.schemas.agents import UserContext
from service.services.agents.domain.subagents.base import BaseSubAgent
from service.services.agents.domain.subagents.utils import pick_text_model

logger = logging.getLogger(__name__)


class PPTXGenerationAgent(BaseSubAgent):
    """Specialized agent for PPTX generation."""

    def __init__(self, model_settings: dict):
        super().__init__(
            name="pptx_gen",
            instructions=(
                "Создавай содержательные презентации PPTX с логичной структурой, "
                "ясными тезисами и фокусом на практическую ценность для аудитории."
            ),
            model_settings=model_settings,
        )

    async def process(self, user_input: str, context: UserContext) -> AsyncGenerator[AgentEvent, None]:
        yield self.start_event("Создаю структуру презентации...")

        safety = await self.evaluate_input_safety(user_input)
        if safety["sensitive"]:
            yield AgentEvent(
                type=EventType.STATUS_UPDATE,
                agent_name=self.name,
                data="⚠️ Чувствительная тема: презентация будет в образовательном и нейтральном формате.",
                metadata=safety["meta"],
            )
        if safety["blocked"]:
            yield AgentEvent(
                type=EventType.ERROR,
                agent_name=self.name,
                data=safety["message"],
                metadata=safety["meta"],
            )
            yield self.complete_event("Генерация PPTX остановлена guardrails")
            return

        try:
            from service.services.agents.domain.client import list_available_models
            from service.services.agents.domain.tools.pptx import generate_pptx

            models = await list_available_models()
            model = pick_text_model(models)
            if not model:
                yield self.error_event("Нет доступных моделей")
            else:
                yield AgentEvent(
                    type=EventType.TOOL_CALL_START,
                    agent_name=self.name,
                    data="Генерирую слайды с помощью ИИ...",
                )

                pptx_bytes, structure = await generate_pptx(user_input, model)
                pptx_b64 = base64.b64encode(pptx_bytes).decode()
                slide_count = len(structure.get("slides", []))

                yield AgentEvent(
                    type=EventType.TOOL_CALL_COMPLETE,
                    agent_name=self.name,
                    data=f"Презентация готова: {slide_count} слайдов",
                )

                reply = (
                    f"✅ **Презентация готова!** ({slide_count} слайдов)\n\n"
                    f"**Тема:** {structure.get('title', user_input)}\n\n"
                    + "\n".join(
                        f"- **Слайд {i+1}:** {s.get('title', '')}"
                        for i, s in enumerate(structure.get("slides", []))
                    )
                    + "\n\n📎 Файл доступен для скачивания ниже."
                )

                async for chunk_event in self.stream_text_chunks(
                    reply,
                    metadata={"pptx_b64": pptx_b64, "filename": "presentation.pptx"},
                ):
                    yield chunk_event
        except Exception as exc:
            logger.exception("PPTX generation failed")
            yield self.error_event(f"Ошибка генерации презентации: {str(exc)}")

        yield self.complete_event("Готово")
