"""Base classes for agent implementations."""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Any, Optional
import logging
import asyncio
import re

from service.services.agents.domain.events import AgentEvent, EventType
from service.services.agents.schemas.agents import UserContext

# Import unified client facade to initialize configured provider (MWS/OpenAI)
from service.services.agents import client as agents_client  # noqa: F401
from service.services.agents.domain.client import create_chat_completion, list_available_models, get_active_provider

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents.

    All agents must implement process() which yields AgentEvent objects.
    """

    def __init__(self, name: str, instructions: str, model_settings: dict):
        self.name = name
        self.instructions = instructions
        self.model_settings = model_settings

    @abstractmethod
    async def process(
        self,
        user_input: str,
        context: UserContext
    ) -> AsyncGenerator[AgentEvent, None]:
        """Main entry point for agent processing.

        Must yield AgentEvent objects that describe what the agent is doing.
        """
        pass


class SimpleStreamingAgent(BaseAgent):
    """Agent that streams responses directly with optional tool use.

    Best for: Q&A, conversational agents that need quick responses.
    Tools are allowed but limited to prevent loops.
    """

    def __init__(
        self,
        name: str,
        instructions: str,
        model_settings: dict,
        tools: list = None,
        input_guardrails: list = None,
        output_guardrails: list = None,
        max_turns: int = 6
    ):
        super().__init__(name, instructions, model_settings)
        self.tools = tools or []
        self.input_guardrails = input_guardrails or []
        self.output_guardrails = output_guardrails or []
        self.max_turns = max_turns

    @staticmethod
    def _split_text_chunks(text: str, chunk_size: int = 220) -> list[str]:
        """Split text into readable stream chunks for UI typing experience."""
        source = str(text or "")
        if not source.strip():
            return []

        chunks: list[str] = []
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
            cut = remaining[:boundary].rstrip()
            if cut:
                chunks.append(cut)
            remaining = remaining[boundary:].lstrip()

        if remaining.strip():
            chunks.append(remaining)
        return chunks

    @staticmethod
    def _extract_text_from_sdk_event(event: Any) -> str | None:
        """Extract textual delta/content from heterogeneous Agents SDK stream events."""
        if event is None:
            return None

        event_type = getattr(event, "type", None) or (event.get("type") if isinstance(event, dict) else None)

        # Direct candidates on event
        for field in ("text", "delta", "content"):
            value = getattr(event, field, None) if not isinstance(event, dict) else event.get(field)
            if isinstance(value, str) and value:
                return value

        raw = getattr(event, "data", None) if not isinstance(event, dict) else event.get("data")

        if raw is not None:
            # Common object fields
            for field in ("delta", "text", "content"):
                value = getattr(raw, field, None) if not isinstance(raw, dict) else raw.get(field)
                if isinstance(value, str) and value:
                    return value

            # Responses API shapes
            if event_type == "raw_response_event":
                r_type = getattr(raw, "type", None) if not isinstance(raw, dict) else raw.get("type")
                if r_type in {
                    "response.output_text.delta",
                    "response.refusal.delta",
                    "response.function_call_arguments.delta",
                }:
                    value = getattr(raw, "delta", None) if not isinstance(raw, dict) else raw.get("delta")
                    if isinstance(value, str) and value:
                        return value

                if r_type in {"response.output_text.done", "response.completed"}:
                    value = getattr(raw, "text", None) if not isinstance(raw, dict) else raw.get("text")
                    if isinstance(value, str) and value:
                        return value

            # message output item shape
            item = getattr(raw, "item", None) if not isinstance(raw, dict) else raw.get("item")
            if item is not None:
                content = getattr(item, "content", None) if not isinstance(item, dict) else item.get("content")
                if isinstance(content, list):
                    for c in content:
                        text = getattr(c, "text", None) if not isinstance(c, dict) else c.get("text")
                        if isinstance(text, str) and text:
                            return text

            response = getattr(raw, "response", None) if not isinstance(raw, dict) else raw.get("response")
            if response is not None:
                output = getattr(response, "output", None) if not isinstance(response, dict) else response.get("output")
                if isinstance(output, list):
                    for out in output:
                        content = getattr(out, "content", None) if not isinstance(out, dict) else out.get("content")
                        if isinstance(content, list):
                            for c in content:
                                text = getattr(c, "text", None) if not isinstance(c, dict) else c.get("text")
                                if isinstance(text, str) and text:
                                    return text

        return None

    async def process(
        self,
        user_input: str,
        context: UserContext
    ) -> AsyncGenerator[AgentEvent, None]:
        """Stream response with optional tool calls."""
        yield AgentEvent(
            type=EventType.AGENT_START,
            agent_name=self.name,
            data=f"Starting {self.name}"
        )

        # MWS keys in this environment can be restricted for /responses,
        # so use chat/completions directly to avoid false 403 in chat UX.
        if get_active_provider() == "mws":
            async for event in self._run_direct_completion(user_input):
                yield event
            return

        try:
            from agents import Agent as SDKAgent, Runner as SDKRunner
            from agents import RunContextWrapper
        except ImportError:
            logger.exception("Failed to import agents SDK")
            yield AgentEvent(
                type=EventType.ERROR,
                agent_name=self.name,
                data="Agent SDK not available"
            )
            return

        try:
            from agents import ModelSettings

            if isinstance(self.model_settings, dict):
                ms = ModelSettings(**self.model_settings)
            else:
                ms = self.model_settings

            agent = SDKAgent(
                name=self.name,
                instructions=self.instructions,
                tools=self.tools,
                input_guardrails=self.input_guardrails,
                output_guardrails=self.output_guardrails,
                model_settings=ms
            )

            try:
                ctx_payload = context.model_dump() if hasattr(context, "model_dump") else context.dict()
            except Exception:
                ctx_payload = {"user_id": str(context.user_id)}

            wrapped_context = RunContextWrapper(ctx_payload)

            result = SDKRunner.run_streamed(
                agent,
                user_input,
                context=wrapped_context,
                max_turns=self.max_turns
            )

            seq = 0
            tool_calls_seen = set()
            collected_text = ""
            streamed_chunks = 0

            async for event in result.stream_events():
                seq += 1
                event_type = getattr(event, "type", None)

                logger.info(f"SDK Event type: {event_type}, event: {event}")

                if event_type == "run_item_stream_event":
                    item = getattr(event, "item", None)
                    if item:
                        tool = getattr(item, "tool", None) or getattr(item, "tool_name", None)
                        if tool:
                            tool_name = getattr(tool, "name", str(tool))
                            if tool_name not in tool_calls_seen:
                                tool_calls_seen.add(tool_name)
                                yield AgentEvent(
                                    type=EventType.TOOL_CALL_START,
                                    agent_name=self.name,
                                    data=f"Using tool: {tool_name}",
                                    seq=seq
                                )

                chunk_text = self._extract_text_from_sdk_event(event)

                if chunk_text:
                    collected_text += chunk_text
                    streamed_chunks += 1
                    yield AgentEvent(
                        type=EventType.STREAM_CHUNK,
                        agent_name=self.name,
                        data=chunk_text,
                        seq=seq
                    )

            if streamed_chunks == 0:
                final_output = getattr(result, "final_output", None)
                fallback_text = final_output if isinstance(final_output, str) else None
                if not fallback_text and final_output is not None:
                    fallback_text = str(final_output)

                for part in self._split_text_chunks(fallback_text or ""):
                    seq += 1
                    yield AgentEvent(
                        type=EventType.STREAM_CHUNK,
                        agent_name=self.name,
                        data=part,
                        seq=seq,
                    )

            yield AgentEvent(
                type=EventType.AGENT_COMPLETE,
                agent_name=self.name,
                data=f"Completed {self.name}"
            )

        except Exception as exc:
            logger.exception(f"Error in {self.name}")

            try:
                selected_model = None
                if isinstance(self.model_settings, dict):
                    selected_model = self.model_settings.get("model")

                if self._is_blocked_chat_model(selected_model):
                    logger.warning("Blocked non-chat model in settings: %s", selected_model)
                    selected_model = None

                if not selected_model:
                    models = await list_available_models()
                    selected_model = self._pick_chat_capable_model(models)

                if selected_model:
                    fallback_response = await create_chat_completion(
                        messages=[
                            {"role": "system", "content": self.instructions[:3000]},
                            {"role": "user", "content": user_input},
                        ],
                        model=selected_model,
                        temperature=0.7,
                        max_tokens=900,
                    )
                    fallback_text = (
                        getattr(getattr(fallback_response.choices[0], "message", None), "content", None)
                        or ""
                    )

                    if fallback_text.strip():
                        for part in self._split_text_chunks(fallback_text):
                            seq += 1
                            yield AgentEvent(
                                type=EventType.STREAM_CHUNK,
                                agent_name=self.name,
                                data=part,
                                metadata={"fallback_model": selected_model},
                                seq=seq,
                            )
                        seq += 1
                        yield AgentEvent(
                            type=EventType.AGENT_COMPLETE,
                            agent_name=self.name,
                            data=f"Completed {self.name}",
                            metadata={"fallback_model": selected_model},
                            seq=seq,
                        )
                        return
            except Exception:
                logger.exception("Fallback completion failed in %s", self.name)

            if isinstance(exc, ConnectionError) or "Connection" in str(exc):
                error_msg = "Connection error occurred. Please try again."
            elif isinstance(exc, TimeoutError) or "timeout" in str(exc).lower():
                error_msg = "Request timed out. Please try again."
            else:
                error_msg = str(exc)

            yield AgentEvent(
                type=EventType.ERROR,
                agent_name=self.name,
                data=error_msg,
                metadata={"error_type": type(exc).__name__, "original_error": str(exc)}
            )

    async def _run_direct_completion(self, user_input: str) -> AsyncGenerator[AgentEvent, None]:
        """Run direct completion path without SDK Responses API."""
        try:
            selected_model = None
            if isinstance(self.model_settings, dict):
                selected_model = self.model_settings.get("model")

            if self._is_blocked_chat_model(selected_model):
                logger.warning("Blocked non-chat model in direct path: %s", selected_model)
                selected_model = None

            if not selected_model:
                models = await list_available_models()
                selected_model = self._pick_chat_capable_model(models)

            if not selected_model:
                yield AgentEvent(
                    type=EventType.ERROR,
                    agent_name=self.name,
                    data="Нет доступной модели для обработки запроса",
                )
                return

            response = await create_chat_completion(
                messages=[
                    {"role": "system", "content": self.instructions[:3000]},
                    {"role": "user", "content": user_input},
                ],
                model=selected_model,
                temperature=0.7,
                max_tokens=900,
            )
            text = (
                getattr(getattr(response.choices[0], "message", None), "content", None)
                or ""
            )

            if not str(text).strip():
                yield AgentEvent(
                    type=EventType.ERROR,
                    agent_name=self.name,
                    data="Модель вернула пустой ответ",
                    metadata={"model": selected_model},
                )
                return

            yield AgentEvent(
                type=EventType.STREAM_CHUNK,
                agent_name=self.name,
                data=str(text),
                metadata={"model": selected_model, "direct_completion": True},
            )
            yield AgentEvent(
                type=EventType.AGENT_COMPLETE,
                agent_name=self.name,
                data=f"Completed {self.name}",
                metadata={"model": selected_model, "direct_completion": True},
            )
        except Exception as exc:
            logger.exception("Direct completion failed in %s", self.name)
            yield AgentEvent(
                type=EventType.ERROR,
                agent_name=self.name,
                data=str(exc),
                metadata={"error_type": type(exc).__name__, "original_error": str(exc)},
            )

    @staticmethod
    def _is_blocked_chat_model(model_id: str | None) -> bool:
        low = str(model_id or "").strip().lower()
        if not low:
            return False
        blocked_markers = ("bge", "e5", "gte", "embed", "embedding", "rerank", "ranker")
        return any(marker in low for marker in blocked_markers)

    @staticmethod
    def _pick_chat_capable_model(models: list[str]) -> str | None:
        """Pick a model that is likely to support chat/completions."""
        blocked_markers = ("bge", "e5", "gte", "embed", "embedding", "rerank", "ranker")
        filtered = [m for m in (models or []) if not any(marker in m.lower() for marker in blocked_markers)]
        if not filtered:
            filtered = models or []
        text_re = re.compile(r"(gpt|qwen|llama|mistral|deepseek|yi|phi|glm|kimi|instruct|chat|alpha)", re.I)
        return next((m for m in filtered if text_re.search(m)), filtered[0] if filtered else None)


class CollectorGeneratorAgent(BaseAgent):
    """Agent with two distinct phases: collect data, then stream response.

    Phase 1 (Collector): Run with tools enabled, gather structured data, no streaming.
    Phase 2 (Generator): Stream human-friendly response using collected data, no tools.

    Best for: Complex tasks like calendar generation, report creation.
    """

    def __init__(
        self,
        name: str,
        instructions: str,
        model_settings: dict,
        tools: list,
        output_schema: Any = None,
        collector_max_turns: int = 4,
        generator_max_turns: int = 3
    ):
        super().__init__(name, instructions, model_settings)
        self.tools = tools
        self.output_schema = output_schema
        self.collector_max_turns = collector_max_turns
        self.generator_max_turns = generator_max_turns

    async def process(
        self,
        user_input: str,
        context: UserContext
    ) -> AsyncGenerator[AgentEvent, None]:
        """Two-phase processing: collector → generator."""

        yield AgentEvent(
            type=EventType.AGENT_START,
            agent_name=self.name,
            data="Starting collector phase",
            metadata={"phase": "collector"}
        )

        collected_data = None
        async for event in self._collector_phase(user_input, context):
            yield event
            if event.type == EventType.STRUCTURED_OUTPUT:
                collected_data = event.data

        yield AgentEvent(
            type=EventType.AGENT_START,
            agent_name=self.name,
            data="Starting generator phase",
            metadata={"phase": "generator"}
        )

        async for event in self._generator_phase(user_input, context, collected_data):
            yield event

        yield AgentEvent(
            type=EventType.AGENT_COMPLETE,
            agent_name=self.name,
            data=f"Completed {self.name}"
        )

    async def _collector_phase(
        self,
        user_input: str,
        context: UserContext
    ) -> AsyncGenerator[AgentEvent, None]:
        """Phase 1: Collect data using tools, return structured output."""
        try:
            from agents import Agent as SDKAgent, Runner as SDKRunner
            from agents import RunContextWrapper, ModelSettings
        except ImportError:
            logger.exception("Failed to import agents SDK")
            yield AgentEvent(
                type=EventType.ERROR,
                agent_name=self.name,
                data="Agent SDK not available"
            )
            return

        try:
            collector_instructions = (
                self.instructions +
                "\n\nФаза COLLECTOR (сбор данных): "
                "используй инструменты целенаправленно, собирай проверяемые факты и структурируй результат. "
                "Не пиши финальный пользовательский ответ. "
                "Если данных недостаточно — явно укажи пробелы и что ещё нужно собрать."
            )

            if isinstance(self.model_settings, dict):
                ms = ModelSettings(**self.model_settings)
            else:
                ms = self.model_settings

            collector = SDKAgent(
                name=f"{self.name}-Collector",
                instructions=collector_instructions,
                tools=self.tools,
                model_settings=ms,
                output_type=self.output_schema
            )

            try:
                ctx_payload = context.model_dump() if hasattr(context, "model_dump") else context.dict()
            except Exception:
                ctx_payload = {"user_id": str(context.user_id)}

            wrapped_context = RunContextWrapper(ctx_payload)

            result = await SDKRunner.run(
                collector,
                user_input,
                context=wrapped_context,
                max_turns=self.collector_max_turns
            )

            final_output = getattr(result, "final_output", None)

            if final_output:
                yield AgentEvent(
                    type=EventType.STRUCTURED_OUTPUT,
                    agent_name=self.name,
                    data=final_output,
                    metadata={"phase": "collector"}
                )
            else:
                yield AgentEvent(
                    type=EventType.STATUS_UPDATE,
                    agent_name=self.name,
                    data="Collector phase completed with no output"
                )

        except Exception as exc:
            logger.exception(f"Error in collector phase for {self.name}")
            yield AgentEvent(
                type=EventType.ERROR,
                agent_name=self.name,
                data=f"Collector error: {str(exc)}",
                metadata={"error_type": type(exc).__name__, "phase": "collector"}
            )

    async def _generator_phase(
        self,
        user_input: str,
        context: UserContext,
        collected_data: Any
    ) -> AsyncGenerator[AgentEvent, None]:
        """Phase 2: Stream human-friendly response using collected data."""
        try:
            from agents import Agent as SDKAgent, Runner as SDKRunner
            from agents import RunContextWrapper, ModelSettings
        except ImportError:
            logger.exception("Failed to import agents SDK")
            yield AgentEvent(
                type=EventType.ERROR,
                agent_name=self.name,
                data="Agent SDK not available"
            )
            return

        try:
            generator_instructions = (
                self.instructions +
                "\n\nФаза GENERATOR (финальный ответ): "
                "используй collected_data из контекста как единую фактическую базу. "
                "НЕ вызывай инструменты. "
                "Сформируй ясный, структурированный и практичный ответ для пользователя. "
                "Если есть неопределённость — обозначь её явно и предложи следующий шаг."
            )

            if isinstance(self.model_settings, dict):
                ms = ModelSettings(**self.model_settings)
            else:
                ms = self.model_settings

            generator = SDKAgent(
                name=f"{self.name}-Generator",
                instructions=generator_instructions,
                tools=[],
                model_settings=ms
            )

            try:
                ctx_payload = context.model_dump() if hasattr(context, "model_dump") else context.dict()
            except Exception:
                ctx_payload = {"user_id": str(context.user_id)}

            ctx_payload["collected_data"] = collected_data

            wrapped_context = RunContextWrapper(ctx_payload)

            result = SDKRunner.run_streamed(
                generator,
                user_input,
                context=wrapped_context,
                max_turns=self.generator_max_turns
            )

            seq = 0
            async for event in result.stream_events():
                seq += 1
                event_type = getattr(event, "type", None)
                logger.info(f"SDK Event: {event_type} - seq: {seq}")

                if event_type == "raw_response_event":
                    raw = getattr(event, "data", None)
                    delta = getattr(raw, "delta", None)
                    logger.info(f"Raw response delta: '{delta}'")
                    if delta:
                        logger.info(f"Yielding STREAM_CHUNK: '{delta}'")
                        yield AgentEvent(
                            type=EventType.STREAM_CHUNK,
                            agent_name=self.name,
                            data=delta,
                            seq=seq,
                            metadata={"phase": "generator"}
                        )

        except Exception as exc:
            logger.exception(f"Error in generator phase for {self.name}")
            yield AgentEvent(
                type=EventType.ERROR,
                agent_name=self.name,
                data=f"Generator error: {str(exc)}",
                metadata={"error_type": type(exc).__name__, "phase": "generator"}
            )
