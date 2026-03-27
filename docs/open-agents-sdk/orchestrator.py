import logging
from agents import Agent, Runner, ModelSettings, OpenAIChatCompletionsModel
from service.agents.client.openai_client import OPENAI_CLIENT
from service.agents.scripts.agents import (
    create_nutrition_agent,
    create_meal_calendar_agent,
)
from service.agents.pydantic.agents import RoutingDecision, UserContext
from service.agents.scripts.guardrail import check_appropriate_language, validate_response_relevance

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    def __init__(self, model_settings: dict):
        self.router = self._create_router_agent(model_settings)
        self.agents = {
            "nutrition": create_nutrition_agent(model_settings),
            "meal_calendar": create_meal_calendar_agent(model_settings),
            "other": create_nutrition_agent(model_settings),
        }

    def _create_router_agent(self, model_settings: dict) -> Agent:
        return Agent(
            name="Роутер-агент",
            instructions=(
                "Анализируй запросы пользователей и определяй категорию:\n"
                "1. Nutrition - вопросы о питании, рецептах, подсчёте калорий\n"
                "2. Meal_Calendar - просьба сгенерировать структурированный план питания\n"
                "3. Other - все остальные запросы\n"
                "Формат ответа только JSON: {\"category\": \"nutrition|meal_calendar|other\"}"
            ),
            model=OpenAIChatCompletionsModel(
                model="gpt-4o-mini",
                openai_client=OPENAI_CLIENT,
            ),
            model_settings=ModelSettings(**model_settings),
            output_type=RoutingDecision,
            input_guardrails=[check_appropriate_language],
        )

    async def route_request(self, query: str, context=None) -> Agent:
        category = None

        def _extract_category(obj):
            if obj is None:
                return None
            # dict-like
            try:
                if isinstance(obj, dict):
                    c = obj.get("category")
                    if isinstance(c, str) and c:
                        return c
            except Exception:
                pass
            # attribute-like
            try:
                c = getattr(obj, "category", None)
                if isinstance(c, str) and c:
                    return c
                # pydantic-style wrapper
                if hasattr(c, "__root__"):
                    root = getattr(c, "__root__", None)
                    if isinstance(root, str) and root:
                        return root
            except Exception:
                pass
            return None

        # Prefer streaming router if available (allows early agent updates and lower latency)
        try:
            # Runner from agents SDK may expose a run_streamed helper (non-async call returning a RunResultStreaming)
            if hasattr(Runner, "run_streamed"):
                # run_streamed typically returns a RunResultStreaming object synchronously
                logger.debug("Orchestrator: invoking run_streamed on router agent for query=%s", (query[:200] if query is not None else None))
                try:
                    result = Runner.run_streamed(self.router, input=query, context=context)
                except TypeError:
                    # some Runner implementations may not accept context kwarg
                    result = Runner.run_streamed(self.router, input=query)

                # Iterate events to try to capture an early structured routing decision
                try:
                    async for event in result.stream_events():
                        etype = getattr(event, "type", None)
                        logger.debug("Orchestrator: stream event type=%s", etype)
                        # event types include run_item_stream_event and agent_updated_stream_event
                        # Try to extract a structured routing decision from run_item events
                        try:
                            item = getattr(event, "item", None)
                            if item is not None:
                                out = getattr(item, "output", None)
                                logger.debug("Orchestrator: run_item output_preview=%s", (str(out)[:200] if out is not None else None))
                                if out is not None:
                                    # If the output is a pydantic model-like object, try to read 'category'
                                    category = _extract_category(out)
                                    if isinstance(category, str) and category:
                                        logger.debug("Orchestrator: found category early=%s", category)
                                        break
                        except Exception:
                            # ignore and continue streaming
                            logger.exception("Orchestrator: failed to parse stream event item")
                except Exception:
                    # If streaming iteration fails, fall back to reading final_output below
                    logger.exception("Error while streaming router events; will try to read final_output")

                # If not found yet, try to read final_output from the result
                try:
                    final = getattr(result, "final_output", None)
                    logger.debug("Orchestrator: run_streamed final_output_preview=%s", (str(final)[:200] if final is not None else None))
                    category = _extract_category(final)
                except Exception:
                    category = None
                # If streaming didn't yield a category, attempt a non-streamed run as a fallback
                if not category and hasattr(Runner, "run"):
                    try:
                        logger.debug("Orchestrator: trying Runner.run fallback for router agent")
                        res = await Runner.run(self.router, query)
                        # Runner.run may return an object with final_output or the final_output itself
                        out = getattr(res, "final_output", None) or res
                        category = _extract_category(out)
                    except Exception:
                        logger.exception("Orchestrator: Runner.run fallback failed")
            else:
                # No streaming API; use regular run
                logger.debug("Orchestrator: invoking Runner.run on router agent for query=%s", (query[:200] if query is not None else None))
                result = await Runner.run(self.router, query)
                category = getattr(getattr(result, "final_output", None), "category", None)
        except Exception:
            logger.exception("Router agent failed; using keyword fallback routing")
            category = None

        # If router didn't produce a valid category, apply a simple keyword-based fallback
        if not category or category not in self.agents:
            q = (query or "").lower()
            if any(k in q for k in ("calendar", "кален", "план")):
                category = "meal_calendar"
            elif any(k in q for k in ("recipe", "рецепт", "калорий", "калл")):
                category = "nutrition"
            else:
                category = "other"

        logger.info("Запрос отнесен к категории: %s", category)
        return self.agents[category]
