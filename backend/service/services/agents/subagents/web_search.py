"""Web search sub-agent."""

import asyncio
import logging
from typing import AsyncGenerator

from service.services.agents.domain.events import AgentEvent, EventType
from service.services.agents.schemas.agents import UserContext
from service.services.agents.subagents.base import BaseSubAgent
from service.services.agents.subagents.utils import pick_text_model

logger = logging.getLogger(__name__)


class WebSearchAgent(BaseSubAgent):
    """Specialized agent for web-search augmented answers."""

    def __init__(self, model_settings: dict):
        super().__init__(
            name="web_search",
            instructions=(
                "Выполняй веб-поиск, извлекай ключевые факты и синтезируй практичный ответ. "
                "Всегда отделяй подтверждённые факты от предположений и указывай источники."
            ),
            model_settings=model_settings,
        )

    async def process(self, user_input: str, context: UserContext) -> AsyncGenerator[AgentEvent, None]:
        yield self.start_event("Запускаю веб-поиск")

        safety = await self.evaluate_input_safety(user_input)
        if safety["sensitive"]:
            yield AgentEvent(
                type=EventType.STATUS_UPDATE,
                agent_name=self.name,
                data="⚠️ Чувствительная тема: показываю только безопасный и нейтральный анализ.",
                metadata=safety["meta"],
            )
        if safety["blocked"]:
            yield AgentEvent(
                type=EventType.ERROR,
                agent_name=self.name,
                data=safety["message"],
                metadata=safety["meta"],
            )
            yield self.complete_event("Веб-поиск остановлен guardrails")
            return

        yield AgentEvent(type=EventType.TOOL_CALL_START, agent_name=self.name, data="Выполняю поиск в интернете...")

        try:
            from service.services.agents.tools.web_search import parse_url, web_search
            from service.services.agents.client import create_chat_completion, list_available_models

            try:
                results = await asyncio.wait_for(web_search(user_input, num_results=5), timeout=16)
            except asyncio.TimeoutError:
                logger.warning("web_search timeout for query: %s", user_input)
                results = []

            yield AgentEvent(
                type=EventType.TOOL_CALL_COMPLETE,
                agent_name=self.name,
                data=f"Найдено результатов: {len(results)}",
            )

            if not results:
                async for chunk_event in self.stream_text_chunks(
                    ""
                    "По внешнему поиску сейчас не удалось получить источники (таймаут или блокировка поиска).\n\n"
                    "Что можно сделать:\n"
                    "1) Уточнить запрос (добавить период/регион).\n"
                    "2) Повторить через 1-2 минуты.\n"
                    "3) Прислать 2-3 ссылки — я сразу сделаю выжимку по ним.\n"
                    ""
                ):
                    yield chunk_event
                yield self.complete_event("Веб-поиск завершён (без внешних источников)")
                return

            parsed_content = []
            for r in results[:2]:
                url = r.get("url", "")
                if not url:
                    continue
                try:
                    parsed = await asyncio.wait_for(parse_url(url, max_chars=2000), timeout=8)
                except asyncio.TimeoutError:
                    logger.debug("parse_url timeout for %s", url)
                    parsed = {}
                if parsed.get("content"):
                    parsed_content.append(parsed)

            search_data = "## Результаты веб-поиска:\n"
            for i, r in enumerate(results, 1):
                search_data += f"\n{i}. **{r.get('title', '')}** ({r.get('url', '')})\n"
                search_data += f"   {r.get('snippet', '')}\n"

            for p in parsed_content:
                search_data += f"\n### Содержимое: {p.get('title', '')}\n{p.get('content', '')[:1500]}\n"

            models = await list_available_models()
            model = pick_text_model(models)
            if not model:
                async for chunk_event in self.stream_text_chunks(search_data):
                    yield chunk_event
            else:
                system_prompt = (
                    "Ты аналитик с доступом к веб-данным. "
                    "Используй ТОЛЬКО предоставленные результаты поиска как основную базу фактов.\n"
                    "Требования к ответу:\n"
                    "1) Краткий вывод в начале (2-4 пункта).\n"
                    "2) Затем структурированные детали с подзаголовками.\n"
                    "3) Если данных мало или есть противоречия — явно это отметь.\n"
                    "4) В конце добавь блок 'Источники' со ссылками.\n"
                    "Пиши на языке пользователя и используй Markdown.\n"
                )
                try:
                    resp = await asyncio.wait_for(
                        create_chat_completion(
                            messages=[
                                {"role": "system", "content": system_prompt + "\n" + search_data},
                                {"role": "user", "content": user_input},
                            ],
                            model=model,
                            temperature=0.5,
                            max_tokens=1500,
                        ),
                        timeout=20,
                    )
                    reply = getattr(resp.choices[0].message, "content", "") or ""
                except asyncio.TimeoutError:
                    logger.warning("LLM synthesis timeout in web_search agent")
                    reply = (
                        "Не удалось дождаться итоговой генерации модели (таймаут). Ниже — собранные данные:\n\n"
                        f"{search_data}"
                    )
                async for chunk_event in self.stream_text_chunks(reply):
                    yield chunk_event
        except Exception as exc:
            logger.exception("Web search failed")
            yield self.error_event(f"Ошибка веб-поиска: {str(exc)}")

        yield self.complete_event("Веб-поиск завершён")
