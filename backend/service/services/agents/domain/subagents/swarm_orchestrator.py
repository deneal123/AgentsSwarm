"""Swarm Orchestrator subagent — synthesizes multimodal context into a robot-swarm instruction."""

import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator

import httpx

from service.services.agents.domain.base import BaseAgent
from service.services.agents.domain.client import create_chat_completion, list_available_models
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
6. НЕ выводи размышления, цепочки мыслей или процесс рассуждений. Только итоговая инструкция.

Пример хорошей инструкции:
"Отправить робота carter01 к координатам (10, 12) на карте Area-7. Избегать препятствий в зоне (5,5)-(8,8). После прибытия передать статус 'mission_complete'."
"""

TERMINAL_STATUSES = {"completed", "failed", "canceled"}
AGENT_SOURCES = {"agent", "agent-sdk", "orchestrator", "runner"}

# Regex to extract and strip <think>...</think> blocks that reasoning models emit
_THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)


def _extract_think(text: str) -> tuple[str, str]:
    """Return (reasoning_text, clean_instruction) — reasoning is shown to the user, not sent to orchestrator."""
    thoughts = _THINK_RE.findall(text)
    reasoning = "\n\n".join(t.strip() for t in thoughts if t.strip())
    clean = _THINK_RE.sub("", text).strip()
    return reasoning, clean


class SwarmOrchestratorAgent(BaseAgent):
    """Subagent that manages the full robot swarm task lifecycle.

    Workflow:
    1. Synthesize a clear orchestrator instruction from the multimodal user context.
    2. Create a task via the external orchestrator REST API.
    3. Poll /task/{id}/events incrementally (proven reliable approach from official examples).
    4. Stream live events to the frontend; extract images, plan updates, agent text.
    5. Use the final task logs as the definitive user-facing reply.
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
            instruction, reasoning = await self._synthesize_instruction(user_input)
        except Exception as exc:
            logger.exception("Failed to synthesize orchestrator instruction")
            yield AgentEvent(type=EventType.ERROR, agent_name=self.name, data=f"Не удалось сформировать инструкцию: {exc}")
            return

        # Emit reasoning block so the UI can show it in a collapsible panel
        if reasoning:
            yield AgentEvent(
                type=EventType.STATUS_UPDATE,
                agent_name=self.name,
                data=reasoning,
                metadata={"event_type": "orchestrator_reasoning", "reasoning": reasoning},
            )

        yield AgentEvent(
            type=EventType.STATUS_UPDATE,
            agent_name=self.name,
            data=f"Инструкция: {instruction[:120]}{'…' if len(instruction) > 120 else ''}",
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
            yield AgentEvent(type=EventType.ERROR, agent_name=self.name, data=f"Не удалось создать задачу: {exc}")
            return

        yield AgentEvent(
            type=EventType.STATUS_UPDATE,
            agent_name=self.name,
            data=f"Задача создана: {task_id}",
            metadata={"event_type": "orchestrator_task_created", "task_id": task_id},
        )

        # Step 3 — fetch initial plan
        try:
            plan = await self._fetch_plan(task_id)
            if plan:
                yield AgentEvent(
                    type=EventType.STATUS_UPDATE,
                    agent_name=self.name,
                    data=f"План: {len(plan)} шаг(ов)",
                    metadata={"event_type": "orchestrator_plan", "task_id": task_id, "plan": plan},
                )
        except Exception:
            pass

        # Step 4 — stream events via REST polling
        final_status = "completed"
        accumulated_agent_text: list[str] = []
        plan_step_agents_seen: set = set()

        try:
            async for orch_event in self._poll_events(task_id):
                meta = orch_event.get("meta") or {}
                source = orch_event.get("source", "")
                message = orch_event.get("message", "")
                event_type = meta.get("event_type", "")
                sdk_event = meta.get("sdk_event", "")
                meta_type = meta.get("type", "")

                # ── Images ──────────────────────────────────────────────────
                if meta_type == "map_image":
                    image_b64 = meta.get("image_b64", "")
                    if image_b64:
                        robots_on_map = meta.get("robots_on_map", 0)
                        yield AgentEvent(
                            type=EventType.STRUCTURED_OUTPUT,
                            agent_name=self.name,
                            data={
                                "type": "orchestrator_images",
                                "task_id": task_id,
                                "image_b64": image_b64,
                                "label": f"Карта ({robots_on_map} роботов)",
                                "mime": meta.get("mime", "image/png"),
                            },
                            metadata={"event_type": "orchestrator_images", "task_id": task_id},
                        )
                        continue

                if meta_type == "route_images":
                    images = meta.get("images") or []
                    winner = meta.get("winner", "")
                    if images:
                        normalized = [
                            {
                                "name": img.get("name", f"route_{i}"),
                                "image_b64": img.get("image_b64", ""),
                                "is_best": img.get("is_best", False) or img.get("name") == winner,
                                "mime": img.get("mime", "image/png"),
                            }
                            for i, img in enumerate(images)
                            if img.get("image_b64")
                        ]
                        if normalized:
                            yield AgentEvent(
                                type=EventType.STRUCTURED_OUTPUT,
                                agent_name=self.name,
                                data={
                                    "type": "orchestrator_images",
                                    "task_id": task_id,
                                    "images": normalized,
                                    "winner": winner,
                                },
                                metadata={"event_type": "orchestrator_images", "task_id": task_id},
                            )
                    continue

                # ── Skip non-text SDK noise ──────────────────────────────────
                if sdk_event == "message_output_created":
                    continue
                if not message or message in {"Task accepted", "Plan created"}:
                    continue
                # Skip noisy agent-sdk internal events (raw_response_event already handled above)
                if source == "agent-sdk" and sdk_event not in {"tool_called"}:
                    continue
                # Skip Python repr of dicts that slipped through as messages
                if message and message.startswith("{'") and message.endswith("}"):
                    continue

                # ── Streaming agent text deltas ──────────────────────────────
                if sdk_event == "raw_response_event" and message:
                    # Skip pure JSON chunks — these are tool call arg leakages, not user text
                    stripped = message.strip()
                    is_pure_json = (
                        (stripped.startswith("{") and stripped.endswith("}"))
                        or (stripped.startswith("[") and stripped.endswith("]"))
                    )
                    if is_pure_json:
                        try:
                            json.loads(stripped)
                            continue
                        except (json.JSONDecodeError, ValueError):
                            pass
                    accumulated_agent_text.append(message)
                    # Accumulate for final STREAM_CHUNK, do not emit as STATUS_UPDATE
                    continue

                # ── Plan updates on step events ──────────────────────────────
                step_id = meta.get("step_id")
                agent_in_step = meta.get("agent", "")
                is_step_event = "step" in event_type and step_id is not None

                if is_step_event and agent_in_step and agent_in_step not in plan_step_agents_seen:
                    plan_step_agents_seen.add(agent_in_step)
                    try:
                        updated_plan = await self._fetch_plan(task_id)
                        if updated_plan:
                            yield AgentEvent(
                                type=EventType.STATUS_UPDATE,
                                agent_name=self.name,
                                data="Обновление плана",
                                metadata={"event_type": "orchestrator_plan", "task_id": task_id, "plan": updated_plan},
                            )
                    except Exception:
                        pass

                # ── Live event for frontend timeline ─────────────────────────
                yield AgentEvent(
                    type=EventType.STATUS_UPDATE,
                    agent_name=self.name,
                    data=message,
                    metadata={
                        "event_type": "orchestrator_event",
                        "task_id": task_id,
                        "orchestrator_event": {
                            "source": source,
                            "message": message,
                            "level": orch_event.get("level", "info"),
                            "ts": orch_event.get("ts", ""),
                            "meta": {k: v for k, v in meta.items() if k not in ("image_b64", "images")},
                        },
                    },
                )

        except Exception as exc:
            logger.exception("Error while streaming orchestrator events for task %s", task_id)
            yield AgentEvent(type=EventType.ERROR, agent_name=self.name, data=f"Ошибка событий оркестратора: {exc}")

        # Step 5 — get final status and task logs for the user reply
        try:
            status_data = await self._get_task_status(task_id)
            final_status = status_data.get("status", "completed")
        except Exception:
            pass

        # Build reply: prefer accumulated streaming text, fall back to task logs
        reply_text = ""
        if accumulated_agent_text:
            reply_text = "".join(accumulated_agent_text).strip()

        if not reply_text:
            try:
                logs = await self._get_task_logs(task_id)
                # Take last meaningful log entries (agent output, not system lines)
                meaningful = [
                    l for l in logs
                    if l and not l.startswith("[info] api:") and not l.startswith("[info] planner: Plan")
                ]
                if meaningful:
                    reply_text = "\n".join(meaningful[-5:])
            except Exception:
                pass

        if not reply_text:
            status_labels = {"completed": "успешно завершена", "failed": "завершена с ошибкой", "canceled": "отменена"}
            reply_text = f"Задача роя роботов {status_labels.get(final_status, final_status)}.\nИдентификатор: `{task_id}`"

        # Emit the actual reply
        yield AgentEvent(type=EventType.STREAM_CHUNK, agent_name=self.name, data=reply_text)

        # Final plan state
        try:
            final_plan = await self._fetch_plan(task_id)
            if final_plan:
                yield AgentEvent(
                    type=EventType.STATUS_UPDATE,
                    agent_name=self.name,
                    data="Итоговый план",
                    metadata={"event_type": "orchestrator_plan", "task_id": task_id, "plan": final_plan},
                )
        except Exception:
            pass

        # Notify frontend of the terminal status before AGENT_COMPLETE
        yield AgentEvent(
            type=EventType.STATUS_UPDATE,
            agent_name=self.name,
            data=f"Задача завершена: {final_status}",
            metadata={"event_type": "orchestrator_status", "status": final_status, "task_id": task_id},
        )

        yield AgentEvent(
            type=EventType.AGENT_COMPLETE,
            agent_name=self.name,
            data="Агент управления роем завершил работу",
            metadata={"task_id": task_id, "final_status": final_status},
        )

    # ------------------------------------------------------------------
    # REST polling (primary approach — proven reliable in orchestrator examples)
    # ------------------------------------------------------------------

    async def _poll_events(self, task_id: str, timeout: int = 300) -> AsyncGenerator[dict]:
        """Incrementally poll /events until task reaches terminal state."""
        base_url = self._get_orchestrator_http_url()
        after_seq = 0
        deadline = asyncio.get_event_loop().time() + timeout
        poll_interval = 0.5

        async with httpx.AsyncClient(timeout=15) as client:
            while asyncio.get_event_loop().time() < deadline:
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

                    # Check terminal status
                    status_resp = await client.get(f"{base_url}/task/{task_id}/status")
                    if status_resp.is_success:
                        task_status = status_resp.json().get("task", {}).get("status", "")
                        if task_status in TERMINAL_STATUSES:
                            # One final poll for any trailing events
                            trail_resp = await client.get(
                                f"{base_url}/task/{task_id}/events",
                                params={"after_seq": after_seq},
                            )
                            if trail_resp.is_success:
                                for event in trail_resp.json().get("events", []):
                                    yield event
                            return

                except Exception as exc:
                    logger.warning("Poll error for orchestrator task %s: %s", task_id, exc)

                await asyncio.sleep(poll_interval)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _synthesize_instruction(self, user_input: str) -> tuple[str, str]:
        """Distil the multimodal context into (instruction, reasoning).

        Reasoning is extracted from <think> blocks and shown to the user in the UI,
        but is never forwarded to the orchestrator.
        """
        messages = [
            {"role": "system", "content": INSTRUCTION_SYNTHESIS_PROMPT},
            {"role": "user", "content": user_input},
        ]
        model = await self._pick_model()
        response = await create_chat_completion(messages=messages, model=model, max_tokens=512, temperature=0.2)
        raw = getattr(getattr(response.choices[0], "message", None), "content", None) or ""
        reasoning, instruction = _extract_think(raw)
        return instruction or user_input[:500], reasoning

    async def _create_orchestrator_task(self, instruction: str) -> str:
        base_url = self._get_orchestrator_http_url()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{base_url}/task", json={"prompt": instruction})
            resp.raise_for_status()
            data = resp.json()
            task_id = data.get("task_id")
            if not task_id:
                raise ValueError(f"Orchestrator did not return task_id: {data}")
            return task_id

    async def _fetch_plan(self, task_id: str) -> list:
        base_url = self._get_orchestrator_http_url()
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{base_url}/task/{task_id}/plan")
            resp.raise_for_status()
            return resp.json().get("plan", [])

    async def _get_task_status(self, task_id: str) -> dict:
        base_url = self._get_orchestrator_http_url()
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{base_url}/task/{task_id}/status")
            resp.raise_for_status()
            return resp.json().get("task", {})

    async def _get_task_logs(self, task_id: str) -> list[str]:
        base_url = self._get_orchestrator_http_url()
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{base_url}/task/{task_id}/logs")
            resp.raise_for_status()
            return resp.json().get("logs", [])

    async def _pick_model(self) -> str:
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
