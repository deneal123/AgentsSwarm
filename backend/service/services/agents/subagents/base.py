"""Base class for specialized sub-agents."""

from abc import abstractmethod
from typing import AsyncGenerator

from service.services.agents.base_agent import BaseAgent
from service.services.agents.events import AgentEvent, EventType
from service.services.agents.pydantic.agents import UserContext


class BaseSubAgent(BaseAgent):
    """Common base for domain-specific sub-agents."""

    def start_event(self, message: str) -> AgentEvent:
        return AgentEvent(type=EventType.AGENT_START, agent_name=self.name, data=message)

    def complete_event(self, message: str) -> AgentEvent:
        return AgentEvent(type=EventType.AGENT_COMPLETE, agent_name=self.name, data=message)

    def error_event(self, message: str) -> AgentEvent:
        return AgentEvent(type=EventType.ERROR, agent_name=self.name, data=message)

    async def evaluate_input_safety(self, user_input: str) -> dict:
        """Run lightweight guardrails before expensive tool/model work.

        Returns shape:
        {
            "blocked": bool,
            "sensitive": bool,
            "meta": dict,
            "message": str | None,
        }
        """
        from service.services.agents.guardrails import check_appropriate_language, check_forbidden_topics

        text = str(user_input or "")
        lowered = text.lower()

        abusive = await check_appropriate_language.guardrail_function(None, None, text)
        forbidden = await check_forbidden_topics.guardrail_function(None, None, text)

        sensitive_markers = (
            "секс",
            "сексуал",
            "эрот",
            "вибратор",
            "интим",
            "porn",
            "sex",
            "adult",
        )
        sensitive = any(marker in lowered for marker in sensitive_markers)

        blocked = bool(abusive.tripwire_triggered or forbidden.tripwire_triggered)
        message = None
        if blocked:
            message = "Запрос затрагивает небезопасную тему. Переформулируйте вопрос в безопасном и образовательном формате."

        meta = {
            "input_guardrails": {
                "abusive": {
                    "tripwire": bool(abusive.tripwire_triggered),
                    "info": abusive.output_info,
                },
                "forbidden_topics": {
                    "tripwire": bool(forbidden.tripwire_triggered),
                    "info": forbidden.output_info,
                },
                "sensitive_topic": {
                    "tripwire": sensitive,
                    "info": {"detected": sensitive},
                },
            }
        }

        return {
            "blocked": blocked,
            "sensitive": sensitive,
            "meta": meta,
            "message": message,
        }

    async def stream_text_event(self, text: str, metadata: dict | None = None) -> AgentEvent:
        """Create a guarded stream chunk event for user-facing text."""
        from service.services.agents.guardrails import fact_check_output

        guarded_text = text
        guardrails_meta: dict[str, object] = {}

        if not str(guarded_text or "").strip():
            # For streaming pipelines empty chunks are expected sometimes.
            # Keep silent chunk instead of replacing it with fallback text.
            return AgentEvent(
                type=EventType.STREAM_CHUNK,
                agent_name=self.name,
                data="",
                metadata={**(metadata or {}), "guardrails": {"empty_chunk": {"tripwire": True}}},
            )

        try:
            fact_check = await fact_check_output.guardrail_function(None, None, guarded_text)
            guardrails_meta["fact_check"] = {
                "tripwire": fact_check.tripwire_triggered,
                "info": fact_check.output_info,
            }
            if fact_check.tripwire_triggered:
                guarded_text = (
                    f"{guarded_text}\n\n"
                    "⚠️ Проверяйте критичные утверждения по независимым источникам."
                )
        except Exception:
            pass

        event_metadata = {**(metadata or {})}
        if guardrails_meta:
            event_metadata["guardrails"] = guardrails_meta

        return AgentEvent(
            type=EventType.STREAM_CHUNK,
            agent_name=self.name,
            data=guarded_text,
            metadata=event_metadata,
        )

    async def stream_text_chunks(
        self,
        text: str,
        metadata: dict | None = None,
        *,
        chunk_size: int = 220,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Yield multiple guarded stream chunks to emulate token streaming UX."""
        source = str(text or "")
        if not source.strip():
            yield await self.stream_text_event("", metadata=metadata)
            return

        remaining = source
        while len(remaining) > chunk_size:
            boundary = max(
                remaining.rfind("\n", 0, chunk_size),
                remaining.rfind(". ", 0, chunk_size),
                remaining.rfind("! ", 0, chunk_size),
                remaining.rfind("? ", 0, chunk_size),
                remaining.rfind(" ", 0, chunk_size),
            )
            if boundary <= int(chunk_size * 0.45):
                boundary = chunk_size

            chunk = remaining[:boundary].rstrip()
            if chunk:
                yield await self.stream_text_event(chunk, metadata=metadata)
            remaining = remaining[boundary:].lstrip()

        if remaining.strip():
            yield await self.stream_text_event(remaining, metadata=metadata)

    @abstractmethod
    async def process(self, user_input: str, context: UserContext) -> AsyncGenerator[AgentEvent, None]:
        raise NotImplementedError
