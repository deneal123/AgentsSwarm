"""Swarm Orchestrator subagent — synthesizes multimodal context into a robot-swarm instruction."""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

import httpx

from service.services.agents.domain.base import BaseAgent
from service.services.agents.domain.client import create_chat_completion, get_active_provider, list_available_models
from service.services.agents.domain.events import AgentEvent, EventType
from service.services.agents.schemas.agents import UserContext
from service.settings import config

logger = logging.getLogger(__name__)

INSTRUCTION_SYNTHESIS_PROMPT = """Ты — специализированный агент, который переводит многомодальный контекст пользователя
в чёткую, однозначную инструкцию для системы управления роем роботов (оркестратора).

Правила:
1. Извлеки ключевую цель: ЧТО должен сделать рой, КУДА, С КАКИМИ параметрами.
2. Все упомянутые координаты, идентификаторы роботов, радиусы, маршруты — сохраняй точно.
3. Если пользователь передал описание изображения или карты — используй эти данные.
4. Формат ответа: одна конкретная инструкция на русском языке, до 500 символов.
5. НЕ добавляй вводные слова, пояснения или форматирование. Только сама инструкция.

Пример хорошей инструкции:
"Отправить робота carter01 к координатам (10, 12) на карте Area-7. Избегать препятствий в зоне (5,5)-(8,8). После прибытия передать статус 'mission_complete'."
"""

TERMINAL_TASK_STATUSES = {"completed", "failed", "canceled", "COMPLETED", "FAILED", "CANCELED"}


class SwarmOrchestratorAgent(BaseAgent):
    """Subagent that manages the full robot swarm task lifecycle.

    Workflow:
    1. Synthesize a clear orchestrator instruction from the multimodal user context.
    2. Create a task via the external orchestrator REST API.
    3. Subscribe to the orchestrator WebSocket and stream live events back.
    4. Yield a brief summary when the task reaches a terminal state.
    """

    def __init__(self, model_settings: dict):
        super().__init__(
            name="swarm_orchestrator",
            instructions=INSTRUCTION_SYNTHESIS_PROMPT,
            model_settings=model_settings,
        )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def process(self, user_input: str, context: UserContext) -> AsyncGenerator[AgentEvent]:
        yield AgentEvent(
            type=EventType.AGENT_START,
            agent_name=self.name,
            data="Запуск агента управления роем роботов",
        )

        # Step 1 — synthesize instruction
        yield AgentEvent(
            type=EventType.STATUS_UPDATE,
            agent_name=self.name,
            data="Формирую инструкцию для оркестратора...",
            metadata={"event_type": "orchestrator_synthesizing"},
        )
        try:
            instruction = await self._synthesize_instruction(user_input)
        except Exception as exc:
            logger.exception("Failed to synthesize orchestrator instruction")
            yield AgentEvent(
                type=EventType.ERROR,
                agent_name=self.name,
                data=f"Не удалось сформировать инструкцию: {exc}",
            )
            return

        yield AgentEvent(
            type=EventType.STATUS_UPDATE,
            agent_name=self.name,
            data=f"Инструкция готова: {instruction[:120]}{'…' if len(instruction) > 120 else ''}",
            metadata={"event_type": "orchestrator_instruction", "instruction": instruction},
        )

        # Step 2 — create task
        yield AgentEvent(
            type=EventType.STATUS_UPDATE,
            agent_name=self.name,
            data="Создаю задачу в оркестраторе...",
            metadata={"event_type": "orchestrator_creating_task"},
        )
        try:
            task_id = await self._create_orchestrator_task(instruction)
        except Exception as exc:
            logger.exception("Failed to create orchestrator task")
            yield AgentEvent(
                type=EventType.ERROR,
                agent_name=self.name,
                data=f"Не удалось создать задачу: {exc}",
            )
            return

        yield AgentEvent(
            type=EventType.STATUS_UPDATE,
            agent_name=self.name,
            data=f"Задача создана: {task_id}",
            metadata={"event_type": "orchestrator_task_created", "task_id": task_id},
        )

        # Step 3 — stream orchestrator WS events
        final_status = "completed"
        try:
            async for orch_event in self._stream_task_events(task_id):
                event_meta = orch_event.get("meta") or {}
                images = event_meta.get("images") or []

                # Emit map / path visualisation images separately
                if images:
                    yield AgentEvent(
                        type=EventType.STRUCTURED_OUTPUT,
                        agent_name=self.name,
                        data={
                            "type": "orchestrator_images",
                            "images": images,
                            "task_id": task_id,
                        },
                        metadata={"event_type": "orchestrator_images", "task_id": task_id},
                    )

                # Detect terminal state
                task_status = (
                    event_meta.get("task_status")
                    or event_meta.get("state")
                    or orch_event.get("status", "")
                )
                if task_status in TERMINAL_TASK_STATUSES:
                    final_status = task_status.lower()

                # Emit live event for frontend timeline
                yield AgentEvent(
                    type=EventType.STATUS_UPDATE,
                    agent_name=self.name,
                    data=orch_event.get("message", ""),
                    metadata={
                        "event_type": "orchestrator_event",
                        "task_id": task_id,
                        "orchestrator_event": {
                            "source": orch_event.get("source", "orchestrator"),
                            "message": orch_event.get("message", ""),
                            "level": orch_event.get("level", "info"),
                            "ts": orch_event.get("ts", ""),
                            "meta": event_meta,
                        },
                    },
                )

                if final_status in {"completed", "failed", "canceled"}:
                    break
        except Exception as exc:
            logger.exception("Error while streaming orchestrator events for task %s", task_id)
            yield AgentEvent(
                type=EventType.ERROR,
                agent_name=self.name,
                data=f"Ошибка получения событий оркестратора: {exc}",
            )

        # Step 4 — brief final reply
        status_labels = {
            "completed": "успешно завершена",
            "failed": "завершена с ошибкой",
            "canceled": "отменена",
        }
        label = status_labels.get(final_status, f"завершена ({final_status})")
        summary = (
            f"Задача роя роботов **{label}**.\n\n"
            f"Идентификатор задачи: `{task_id}`\n"
            f"Инструкция оркестратору: {instruction}"
        )
        yield AgentEvent(type=EventType.STREAM_CHUNK, agent_name=self.name, data=summary)
        yield AgentEvent(
            type=EventType.AGENT_COMPLETE,
            agent_name=self.name,
            data="Агент управления роем завершил работу",
            metadata={"task_id": task_id, "final_status": final_status},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _synthesize_instruction(self, user_input: str) -> str:
        """Use an LLM to distil the multimodal context into a single orchestrator instruction."""
        messages = [
            {"role": "system", "content": INSTRUCTION_SYNTHESIS_PROMPT},
            {"role": "user", "content": user_input},
        ]
        model = await self._pick_model()
        response = await create_chat_completion(messages=messages, model=model, max_tokens=512, temperature=0.2)
        text = getattr(getattr(response.choices[0], "message", None), "content", None) or ""
        return text.strip() or user_input[:500]

    async def _create_orchestrator_task(self, instruction: str) -> str:
        """POST the instruction to the external orchestrator and return task_id."""
        base_url = self._get_orchestrator_http_url()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{base_url}/task", json={"prompt": instruction})
            resp.raise_for_status()
            data = resp.json()
            task_id = data.get("task_id")
            if not task_id:
                raise ValueError(f"Orchestrator did not return task_id: {data}")
            return task_id

    async def _stream_task_events(self, task_id: str) -> AsyncGenerator[dict]:
        """Connect to the orchestrator WebSocket and yield raw event dicts."""
        try:
            import websockets
        except ImportError:
            raise RuntimeError("websockets package is required for orchestrator streaming. Install it with: pip install websockets")

        ws_url = f"{self._get_orchestrator_ws_url()}/ws/task/{task_id}"
        logger.info("Connecting to orchestrator WebSocket: %s", ws_url)

        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
                async for raw_message in ws:
                    try:
                        if isinstance(raw_message, bytes):
                            raw_message = raw_message.decode()
                        data = json.loads(raw_message)
                        yield data

                        # Check if task has reached a terminal state via socket payload
                        meta = data.get("meta") or {}
                        task_status = (
                            meta.get("task_status")
                            or meta.get("state")
                            or data.get("status", "")
                        )
                        if task_status in TERMINAL_TASK_STATUSES:
                            logger.info("Orchestrator task %s reached terminal state: %s", task_id, task_status)
                            return
                    except json.JSONDecodeError:
                        logger.warning("Non-JSON message from orchestrator WS: %s", raw_message[:200])
        except Exception as exc:
            # Fallback: poll events via REST if WS fails
            logger.warning("Orchestrator WS failed (%s), falling back to REST polling", exc)
            async for event in self._poll_task_events_rest(task_id):
                yield event

    async def _poll_task_events_rest(self, task_id: str) -> AsyncGenerator[dict]:
        """Fallback: poll /task/{id}/events via REST when WS is unavailable."""
        base_url = self._get_orchestrator_http_url()
        after_seq = 0
        max_polls = 300  # 5 minutes at 1s interval
        polls = 0

        async with httpx.AsyncClient(timeout=15) as client:
            while polls < max_polls:
                polls += 1
                try:
                    resp = await client.get(
                        f"{base_url}/task/{task_id}/events",
                        params={"after_seq": after_seq},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    events = data.get("events", [])
                    after_seq = data.get("last_seq", after_seq)

                    for event in events:
                        yield event
                        meta = event.get("meta") or {}
                        task_status = meta.get("task_status") or meta.get("state") or ""
                        if task_status in TERMINAL_TASK_STATUSES:
                            return

                    # Check task status separately
                    status_resp = await client.get(f"{base_url}/task/{task_id}/status")
                    if status_resp.is_success:
                        task_info = status_resp.json().get("task", {})
                        if task_info.get("status") in TERMINAL_TASK_STATUSES:
                            return
                except Exception as exc:
                    logger.warning("REST poll error for task %s: %s", task_id, exc)

                await asyncio.sleep(1)

    async def _pick_model(self) -> str:
        """Pick a suitable chat model from the active provider."""
        if isinstance(self.model_settings, dict) and self.model_settings.get("model"):
            return self.model_settings["model"]
        models = await list_available_models()
        blocked = ("bge", "e5", "gte", "embed", "embedding", "rerank", "ranker")
        filtered = [m for m in (models or []) if not any(b in m.lower() for b in blocked)]
        return filtered[0] if filtered else (models[0] if models else "gpt-4o-mini")

    @staticmethod
    def _get_orchestrator_http_url() -> str:
        url = getattr(config.agents, "orchestrator_url", "") or "http://localhost:8100"
        return url.rstrip("/")

    @staticmethod
    def _get_orchestrator_ws_url() -> str:
        http = SwarmOrchestratorAgent._get_orchestrator_http_url()
        if http.startswith("https://"):
            return "wss://" + http[8:]
        if http.startswith("http://"):
            return "ws://" + http[7:]
        return http
