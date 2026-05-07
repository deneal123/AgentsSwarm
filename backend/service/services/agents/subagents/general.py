"""General fallback assistant agent."""

from service.services.agents.base_agent import SimpleStreamingAgent
from service.services.agents.guardrails import (
    check_appropriate_language,
    check_forbidden_topics,
    ensure_non_empty_response,
    fact_check_output,
    validate_response_relevance,
)
from service.services.agents.tools import DEFAULT_FUNCTION_TOOLS

GENERAL_PROMPT = """Ты — GPTHub, универсальный ведущий ИИ-ассистент для рабочих задач.

Режим работы:
1) Сначала пойми цель пользователя и ограничения.
2) Дай практичное решение с чёткими шагами, без воды.
3) Если данных мало — явно обозначь допущения и предложи лучший следующий шаг.

Стандарт качества ответа:
- Пиши на языке пользователя.
- Если запрос написан на русском (кириллица), отвечай строго на русском.
- Служебные подтверждения (включая запоминание фактов) также давай на русском.
- Сохраняй точность: не выдумывай факты, API и ссылки.
- Для сложных тем структурируй ответ в Markdown (краткий вывод → детали → следующие шаги).
- Приводи альтернативы, когда есть компромиссы (скорость/качество/стоимость/риски).
- Для кода: ориентируйся на промышленный подход, пограничные случаи и проверяемость.

Тон: уверенный, деловой, дружелюбный. Максимум пользы в минимуме текста.
"""


class GeneralAgent(SimpleStreamingAgent):
    """Universal assistant used for standard requests."""

    def __init__(self, model_settings: dict):
        super().__init__(
            name="general",
            instructions=GENERAL_PROMPT,
            model_settings=model_settings,
            tools=DEFAULT_FUNCTION_TOOLS,
            input_guardrails=[
                check_appropriate_language,
                check_forbidden_topics,
            ],
            output_guardrails=[
                ensure_non_empty_response,
                fact_check_output,
                validate_response_relevance,
            ],
            max_turns=8,
        )
