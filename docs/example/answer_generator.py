from typing import Optional, Any, Dict
from datetime import datetime, timezone
import json
from dataclasses import dataclass, field
from service.agents.modules.base import MetaModule
from service.agents.scripts.orchestrator import OrchestratorAgent
from agents import RawResponsesStreamEvent, Runner, TResponseInputItem  # external dependency
from service.agents.pydantic.agents import UserContext
from service.agents.pydantic.models import AgentsResponse
import logging
import asyncio


log = logging.getLogger(__name__)


from service.agents.modules.buffers import (
    buffer_llm_query,
    buffer_llm_responses,
)


@dataclass
class AnswerGenerator(MetaModule):
    config: Optional[Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        super().__init__()
        self.model_settings = self.config.get("model_settings")
        self._answer_task_running = False
        self._answer_task: Optional[asyncio.Task] = None
        self.inputs: Dict[str, list] = {}
        self.agent = self.get_smart_agents(self.model_settings)

    def get_smart_agents(self, model_settings: dict) -> OrchestratorAgent:
        return OrchestratorAgent(model_settings)

    async def run_cycle(self):
        try:
            if not buffer_llm_query.empty():
                query_data = buffer_llm_query.get()

                if query_data:
                    current_text = query_data.query
                    current_user_id = query_data.user_id
                    current_request_time = query_data.request_time
                    current_session = getattr(query_data, "session", None)

                    if not self._answer_task_running:
                        self._answer_task_running = True
                        # remember session for the running task
                        self._current_session = current_session
                        self._answer_task = asyncio.create_task(
                            self._process_answers(current_text, current_user_id, current_request_time)
                        )

        except Exception as ex:
            log.exception("Проблема при инференсе llm модели: %s", ex)
            # Do not raise BaseException; just log and continue

    async def _process_answers(self, text: str, user_id: str | None = None, request_time: datetime | None = None) -> None:
        try:
            context = UserContext(
                user_id=user_id,
                request_time=request_time or datetime.now(timezone.utc),
                previous_questions=self.inputs.get(user_id, []),
                session=getattr(self, "_current_session", None) or current_session,
            )

            orchestrator = self.get_smart_agents(self.model_settings)
            selected_agent = await orchestrator.route_request(text)

            result = await Runner.run(
                starting_agent=selected_agent,
                input=text,
                context=context
            )

            response = getattr(result, 'final_output', None)

            if response:
                if user_id not in self.inputs:
                    self.inputs[user_id] = []
                self.inputs[user_id].append({"content": text, "role": "user"})
                self.inputs[user_id].append({"content": response, "role": "assistant"})

                answer = AgentsResponse(
                    answer=str(response),
                    user_id=str(user_id or ""),
                )

                log.info(
                    "Agent name: %s; Final answer for user %s",
                    getattr(result.last_agent, 'name', None),
                    user_id,
                )
                buffer_llm_responses.put(answer)

            self.agent = getattr(result, 'last_agent', self.agent)

        except Exception as ex:
            log.exception("Ошибка в процессе генерации ответа агентом: %s", ex)
        finally:
            self._answer_task_running = False
            # cleanup session reference
            if hasattr(self, "_current_session"):
                try:
                    delattr(self, "_current_session")
                except Exception:
                    pass

    async def stop(self):
        if self._answer_task and not self._answer_task.done():
            self._answer_task.cancel()
            try:
                await self._answer_task
            except asyncio.CancelledError:
                pass
        await super().async_stop()