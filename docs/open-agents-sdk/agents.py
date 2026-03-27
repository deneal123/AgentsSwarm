import logging
from agents import Agent, ModelSettings, OpenAIChatCompletionsModel
from service.agents.scripts.function import faq_lookup, fetch_context, fetch_recipe, calorie_lookup, bulk_fetch_recipe, bulk_calorie_lookup
from service.agents.scripts.guardrail import validate_response_relevance, validate_calendar_schema
from service.agents.client.openai_client import OPENAI_CLIENT
from service.agents.pydantic.agents import MealCalendarOutput

logger = logging.getLogger(__name__)


def create_nutrition_agent(model_settings: dict) -> Agent:
    """Agent for general nutrition conversation (recipes, calories, substitutions).

    Does NOT provide medical advice; should recommend consulting a professional
    for medical/diet needs.
    """
    return Agent(
        name="Nutrition-Agent",
        instructions=(
            "Вы — эксперт по питанию и приготовлению еды. Помогайте с рецептами,"
            "разработкой планов питания, подбором замен ингредиентов и подсчётом калорий."
            "Не давайте медицинских рекомендаций — при необходимости направляйте к специалисту."
        ),
        model=OpenAIChatCompletionsModel(model="gpt-4o-mini", openai_client=OPENAI_CLIENT),
        model_settings=ModelSettings(**model_settings),
        tools=[faq_lookup, fetch_context, fetch_recipe, calorie_lookup],
        output_guardrails=[validate_response_relevance],
    )


def create_meal_calendar_agent(model_settings: dict) -> Agent:
    """Agent that produces structured meal-plan calendars.

    Output should conform to MealCalendarOutput Pydantic model (JSON).
    The guardrail `validate_calendar_schema` enforces structure and length.
    """
    agent = Agent(
        name="MealCalendar-Agent",
        instructions=(
            "Генерируй план питания на указанный период. Выход — строго JSON с полем 'calendar',"
            "массива объектов {date: YYYY-MM-DD, meals: [{name, calories, ingredients}] }" 
            "\n\nВажно: чтобы минимизировать число вызовов внешних функций/инструментов, при возможности"
            "сначала сгенерируй набор блюд и приёмы пищи для целого дня (например, завтрак/обед/ужин),"
            "а затем, если нужен внешний поиск рецепта или проверка калорий, используй batch-инструменты"
            "`bulk_fetch_recipe` и `bulk_calorie_lookup` с массивом запросов за один вызов. Это позволит"
            "агенту сделать значительно меньше инструмент-вызовов и избежать исчерпания лимита ходов."
        ),
        model=OpenAIChatCompletionsModel(model="gpt-4o-mini", openai_client=OPENAI_CLIENT),
        model_settings=ModelSettings(**model_settings),
        tools=[fetch_context, bulk_fetch_recipe, bulk_calorie_lookup, fetch_recipe, calorie_lookup],
        output_guardrails=[validate_calendar_schema],
        output_type=MealCalendarOutput,
    )
    # opt into two-phase execution: collect tools and structured calendar first (non-streamed),
    # then stream human-friendly narration. Runner checks this flag to switch flow.
    try:
        setattr(agent, "two_phase", True)
    except Exception:
        # best-effort: if Agent objects are immutable, ignore and let Runner fall back to name matching
        pass
    return agent