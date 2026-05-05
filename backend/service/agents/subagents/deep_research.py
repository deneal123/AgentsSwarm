"""Deep research sub-agent."""

import logging
from typing import AsyncGenerator

from service.agents.events import AgentEvent, EventType
from service.agents.pydantic.agents import UserContext
from service.agents.subagents.base import BaseSubAgent
from service.agents.subagents.utils import pick_text_model

logger = logging.getLogger(__name__)


class DeepResearchAgent(BaseSubAgent):
    """Specialized agent for deep research flows."""

    def __init__(self, model_settings: dict):
        super().__init__(
            name="deep_research",
            instructions=(
                "Проводи глубокий ресерч: формируй гипотезы, собирай источники, "
                "сопоставляй точки зрения и выдавай структурированный аналитический отчёт с выводами."
            ),
            model_settings=model_settings,
        )

    async def process(self, user_input: str, context: UserContext) -> AsyncGenerator[AgentEvent, None]:
        yield self.start_event("Запускаю глубокий ресерч")

        safety = await self.evaluate_input_safety(user_input)
        if safety["sensitive"]:
            yield AgentEvent(
                type=EventType.STATUS_UPDATE,
                agent_name=self.name,
                data="⚠️ Обнаружена чувствительная тема — применяю усиленные guardrails и нейтральный тон.",
                metadata=safety["meta"],
            )
        if safety["blocked"]:
            yield AgentEvent(
                type=EventType.ERROR,
                agent_name=self.name,
                data=safety["message"],
                metadata=safety["meta"],
            )
            yield self.complete_event("Ресерч остановлен guardrails")
            return

        try:
            from service.agents.client import list_available_models
            from service.agents.tools.deep_research import deep_research

            models = await list_available_models()
            model = pick_text_model(models)
            if not model:
                yield self.error_event("Нет доступной модели для ресерча")
            else:
                async for chunk in deep_research(user_input, model):
                    yield await self.stream_text_event(str(chunk))
        except Exception as exc:
            logger.exception("Deep research failed")
            yield self.error_event(f"Ошибка ресерча: {str(exc)}")

        yield self.complete_event("Глубокий ресерч завершён")
