"""Adapter for OpenAI Agents SDK execution of plan steps.

Uses build_openai_client() to support OpenAI or vLLM providers via env.
Streams user-facing events through PlanRunner via StreamCollector.
"""

from __future__ import annotations

import contextlib
import logging
import os
from functools import lru_cache
from typing import Iterable, Optional

from agents import Agent, ModelSettings, RunConfig, Runner
from agents.mcp import MCPServer, MCPServerSse, MCPServerStdio, MCPServerStdioParams, MCPServerStreamableHttp
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from pydantic import BaseModel, Field

from orchestrator.agents import prompts
from orchestrator.agents.mcp import MCPServerConfig
from orchestrator.agents.router import get_router_config
from orchestrator.services.guardrails import prompt_input_guardrail, router_output_guardrail
from orchestrator.services.openai_client import build_openai_client
from orchestrator.services.plan_runner import AgentHandoffExecutor, HandoffResult
from orchestrator.services.streaming import StreamCollector, StreamEvent
from orchestrator.utils.env import env_bool, env_float

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client():
    return build_openai_client()


class RoutingDecision(BaseModel):
    """Структурированный ответ роутера."""

    category: str = Field(description="router label: robot_info|navigation|swarm_coord|general")
    reason: str | None = Field(default=None, description="why the route was chosen")
    target_robots: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None)


def _model_settings() -> ModelSettings:
    temp = env_float("AGENTS_TEMPERATURE", 0.3)
    top_p = env_float("AGENTS_TOP_P", None)
    max_tokens = env_float("AGENTS_MAX_OUTPUT_TOKENS", None)
    kwargs: dict = {"temperature": temp}
    if top_p is not None:
        kwargs["top_p"] = top_p
    if max_tokens is not None:
        kwargs["max_tokens"] = int(max_tokens)
    return ModelSettings(**kwargs)


def _model_name() -> str:
    return os.getenv("AGENTS_MODEL", "gpt-4o-mini")


def _model_instance() -> OpenAIChatCompletionsModel:
    """Return a model instance so RunConfig never sees a slash-prefixed string.

    The Agents SDK multi-provider resolver breaks on names like 'google/gemini-...'
    because it treats the part before '/' as a provider prefix.  Passing an explicit
    OpenAIChatCompletionsModel instance bypasses that resolver entirely.
    """
    return OpenAIChatCompletionsModel(model=_model_name(), openai_client=_client())


def _run_config() -> RunConfig:
    return RunConfig(
        model=_model_instance(),
        model_settings=_model_settings(),
        nest_handoff_history=env_bool("AGENTS_NEST_HANDOFF_HISTORY", False),
        tracing_disabled=env_bool("AGENTS_TRACING_DISABLED", True),
    )


# Mapping from agent name to its system prompt.
_AGENT_PROMPTS: dict[str, str] = {
    "Router": prompts.ROUTER_PROMPT,
    "RobotInfo": prompts.ROBOT_INFO_PROMPT,
    "Navigation": prompts.NAVIGATION_PROMPT,
    "SwarmCoordinator": prompts.SWARM_PROMPT,
    "General": prompts.GENERAL_FALLBACK_PROMPT,
}


def _agent_prompt(agent_name: str) -> str:
    return _AGENT_PROMPTS.get(agent_name, prompts.GENERAL_FALLBACK_PROMPT)


def _mcp_servers(configs: Iterable[MCPServerConfig]) -> list[MCPServer]:
    servers: list[MCPServer] = []
    for cfg in configs:
        if cfg.transport == "sse":
            servers.append(MCPServerSse(params={"url": cfg.url}, name=cfg.name))
        elif cfg.transport == "streamable-http":
            servers.append(MCPServerStreamableHttp(params={"url": cfg.url}, name=cfg.name))
        else:
            params: MCPServerStdioParams = {
                "command": cfg.command,
                "args": cfg.args,
                "env": cfg.env or {},
            }
            servers.append(MCPServerStdio(params=params, name=cfg.name))
    return servers


def _build_agent(agent_name: str, mcp_configs: Iterable[MCPServerConfig] | None = None) -> Agent:
    return Agent(
        name=agent_name,
        instructions=_agent_prompt(agent_name),
        model=OpenAIChatCompletionsModel(model=_model_name(), openai_client=_client()),
        model_settings=_model_settings(),
        mcp_servers=_mcp_servers(mcp_configs or []),
    )


def _router_agent() -> Agent:
    cfg = get_router_config()
    handoff_agents: list[Agent] = [
        _build_agent(
            agent_name=handoff["name"],
            mcp_configs=handoff.get("mcp_servers", []),
        )
        for handoff in cfg.get("handoffs", [])
    ]
    return Agent(
        name="Router",
        instructions=cfg.get("instructions", prompts.ROUTER_PROMPT),
        model=OpenAIChatCompletionsModel(model=_model_name(), openai_client=_client()),
        model_settings=_model_settings(),
        handoffs=handoff_agents,
        output_type=RoutingDecision,
        input_guardrails=[prompt_input_guardrail],
        output_guardrails=[router_output_guardrail],
    )


def _mcp_configs_for(agent_name: str) -> list[MCPServerConfig]:
    for handoff in get_router_config().get("handoffs", []):
        if handoff.get("name") == agent_name:
            return handoff.get("mcp_servers", [])
    return []


class AgentsSDKExecutor(AgentHandoffExecutor):
    def __init__(
        self,
        stream_collector: Optional[StreamCollector] = None,
        step_delay: float = 0.05,
    ) -> None:
        self._step_delay = step_delay
        self._sc = stream_collector

    async def _record_stream(
        self,
        task_id: str,
        event_type: str,
        meta: Optional[dict] = None,
        message: str = "",
    ) -> None:
        if not self._sc:
            return
        self._sc.record(
            StreamEvent(
                task_id=task_id,
                source="agent-sdk",
                message=message or f"SDK event: {event_type}",
                level="info",
                meta=meta or {"event_type": event_type},
            )
        )

    @staticmethod
    def _collect_mcp_servers(agent: object) -> list[MCPServer]:
        servers: list[MCPServer] = list(getattr(agent, "mcp_servers", None) or [])
        for handoff in getattr(agent, "handoffs", None) or []:
            if isinstance(handoff, Agent):
                servers.extend(getattr(handoff, "mcp_servers", None) or [])
        return servers

    async def execute(self, task_id: str, step, attempt: int) -> HandoffResult:
        agent = _router_agent() if step.agent == "Router" else _build_agent(
            step.agent, mcp_configs=_mcp_configs_for(step.agent)
        )
        run_config = _run_config()

        async with contextlib.AsyncExitStack() as stack:
            for server in self._collect_mcp_servers(agent):
                await stack.enter_async_context(server)

            return await self._run_agent(task_id, step, attempt, agent, run_config)

    async def _run_agent(self, task_id: str, step, attempt: int, agent: Agent, run_config: RunConfig) -> HandoffResult:
        try:
            run_streamed = getattr(Runner, "run_streamed", None)
            if run_streamed:
                result = run_streamed(agent, input=step.description, run_config=run_config)
                try:
                    async for ev in result.stream_events():  # type: ignore[attr-defined]
                        etype = getattr(ev, "type", "event")
                        item = getattr(ev, "item", None)
                        payload = getattr(ev, "name", None)
                        if item is not None and getattr(item, "output", None):
                            payload = str(item.output)
                        await self._record_stream(
                            task_id,
                            event_type=etype,
                            meta={"agent": step.agent, "attempt": attempt, "sdk_event": etype},
                            message=payload or f"SDK event: {etype}",
                        )
                except Exception:
                    logger.exception("Failed to consume streaming events", extra={"task_id": task_id})

                output = getattr(result, "final_output", None) or getattr(result, "output", None)
                message = str(output) if output is not None else ""
                try:
                    parsed = result.final_output_as(RoutingDecision)
                    if parsed:
                        message = parsed.reason or parsed.category or message
                except Exception:
                    pass
                return HandoffResult(success=True, message=message)

            result = await Runner.run(agent, step.description, run_config=run_config)
            output = getattr(result, "final_output", None) or result
            return HandoffResult(success=True, message=str(output) if output is not None else "")

        except Exception as exc:
            logger.exception(
                "Agents SDK execution failed",
                extra={"task_id": task_id, "step_id": step.id},
            )
            return HandoffResult(
                success=False,
                message=str(exc),
                user_message="Шаг не выполнен из-за ошибки агента",
                retryable=False,
            )


__all__ = ["AgentsSDKExecutor"]
