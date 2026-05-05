"""Image generation sub-agent."""

import logging
from typing import AsyncGenerator

from service.agents.events import AgentEvent, EventType
from service.agents.pydantic.agents import UserContext
from service.agents.subagents.base import BaseSubAgent
from service.agents.subagents.utils import pick_image_model, pick_text_model

logger = logging.getLogger(__name__)


class ImageGenerationAgent(BaseSubAgent):
    """Specialized agent for image generation / fallback prompt synthesis."""

    def __init__(self, model_settings: dict):
        super().__init__(
            name="image_gen",
            instructions=(
                "Генерируй изображения по запросу пользователя; "
                "если генерация недоступна — создавай качественный готовый промпт для генератора изображений."
            ),
            model_settings=model_settings,
        )

    async def _build_prompt_fallback(self, user_input: str, models: list[str]) -> str:
        from service.agents.client import create_chat_completion

        text_model = pick_text_model(models)
        if not text_model:
            return ""

        resp = await create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Пользователь хочет сгенерировать изображение, но прямой API генерации недоступен. "
                        "Сформируй ОДИН качественный англоязычный промпт для SDXL / Flux / DALL-E. "
                        "Сделай его детальным и управляемым: subject, scene, composition, lighting, style, mood, camera/lens, colors, details. "
                        "Добавь негативный промпт (что исключить) и краткие рекомендации по вариациям. "
                        "Выведи результат в Markdown-блоках: 'Промпт', 'Негативный промпт', 'Быстрые вариации'."
                    ),
                },
                {"role": "user", "content": user_input},
            ],
            model=text_model,
            temperature=0.7,
            max_tokens=500,
        )
        return getattr(resp.choices[0].message, "content", "") or ""

    async def process(self, user_input: str, context: UserContext) -> AsyncGenerator[AgentEvent, None]:
        yield self.start_event("Запускаю генерацию изображения")

        safety = await self.evaluate_input_safety(user_input)
        if safety["sensitive"]:
            yield AgentEvent(
                type=EventType.STATUS_UPDATE,
                agent_name=self.name,
                data="⚠️ Чувствительная тема: включён безопасный режим генерации.",
                metadata=safety["meta"],
            )
        if safety["blocked"]:
            yield AgentEvent(
                type=EventType.ERROR,
                agent_name=self.name,
                data=safety["message"],
                metadata=safety["meta"],
            )
            yield self.complete_event("Генерация изображения остановлена guardrails")
            return

        try:
            from service.agents.client import create_chat_completion, get_openai_client, list_available_models

            models = await list_available_models()
            image_model = pick_image_model(models)

            if image_model:
                yield AgentEvent(
                    type=EventType.TOOL_CALL_START,
                    agent_name=self.name,
                    data=f"Генерирую изображение моделью {image_model}",
                )

                client = get_openai_client()
                if client:
                    try:
                        response = await client.images.generate(
                            model=image_model,
                            prompt=user_input,
                            n=1,
                            size="1024x1024",
                        )
                        if response.data:
                            image_url = response.data[0].url or ""
                            b64 = getattr(response.data[0], "b64_json", None) or ""
                            yield await self.stream_text_event(
                                f"![Generated Image]({image_url})" if image_url else "Изображение сгенерировано.",
                                metadata={"image_url": image_url, "b64_json": b64, "model": image_model},
                            )
                        else:
                            prompt_fallback = await self._build_prompt_fallback(user_input, models)
                            if prompt_fallback.strip():
                                async for chunk_event in self.stream_text_chunks(
                                    (
                                        "Прямая генерация сейчас недоступна, но я подготовил качественный промпт для внешнего генератора:\n\n"
                                        f"{prompt_fallback}"
                                    ),
                                    metadata={"fallback": "prompt_only", "model": image_model},
                                ):
                                    yield chunk_event
                            else:
                                yield await self.stream_text_event("Модель не вернула изображение. Попробуйте другой запрос.")
                    except Exception as img_exc:
                        logger.warning("Image generation API failed: %s", img_exc)
                        prompt_fallback = ""
                        try:
                            prompt_fallback = await self._build_prompt_fallback(user_input, models)
                        except Exception:
                            logger.debug("Prompt fallback generation failed", exc_info=True)

                        if prompt_fallback.strip():
                            async for chunk_event in self.stream_text_chunks(
                                (
                                    f"Прямая генерация изображений временно недоступна (модель: {image_model}). "
                                    "Ниже — готовый промпт для генератора изображений:\n\n"
                                    f"{prompt_fallback}"
                                ),
                                metadata={"fallback": "prompt_only", "model": image_model},
                            ):
                                yield chunk_event
                        else:
                            yield await self.stream_text_event(
                                (
                                    f"Прямая генерация изображений временно недоступна (модель: {image_model}). "
                                    "Попробуйте позже или опишите запрос иначе."
                                ),
                            )
                else:
                    prompt_fallback = await self._build_prompt_fallback(user_input, models)
                    if prompt_fallback.strip():
                        async for chunk_event in self.stream_text_chunks(
                            (
                                "Сервис прямой генерации недоступен, но я подготовил качественный промпт:\n\n"
                                f"{prompt_fallback}"
                            ),
                            metadata={"fallback": "prompt_only", "model": image_model},
                        ):
                            yield chunk_event
                    else:
                        yield await self.stream_text_event(
                            (
                                f"Прямая генерация изображений временно недоступна (модель: {image_model}). "
                                "Попробуйте позже или опишите запрос иначе."
                            ),
                        )
            else:
                reply = await self._build_prompt_fallback(user_input, models)
                if reply.strip():
                    async for chunk_event in self.stream_text_chunks(reply):
                        yield chunk_event
        except Exception as exc:
            logger.exception("Image generation failed")
            yield self.error_event(f"Ошибка генерации изображения: {str(exc)}")

        yield self.complete_event("Генерация изображения завершена")
