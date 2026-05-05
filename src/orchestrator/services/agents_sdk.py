"""Adapter for OpenAI Agents SDK execution of plan steps.

Uses build_openai_client() to support OpenAI or vLLM providers via env.
Falls back to simple agent-per-step execution (no MCP tools yet); still
streams user-facing errors through PlanRunner.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Iterable, Optional

from agents import Agent, ModelSettings, RunConfig, Runner
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from agents.mcp import MCPServer, MCPServerStdio, MCPServerStdioParams
from pydantic import BaseModel, Field

try:
    from agents.mcp import MCPServerSse  # openai-agents >= 0.4
    _HAS_SSE = True
except ImportError:
    _HAS_SSE = False

from orchestrator.agents import prompts
from orchestrator.agents.router import get_router_config
from orchestrator.agents.mcp import MCPServerConfig
from orchestrator.services.openai_client import build_openai_client
from orchestrator.services.plan_runner import AgentHandoffExecutor, HandoffResult
from orchestrator.services.streaming import StreamCollector, StreamEvent
from orchestrator.services.guardrails import prompt_input_guardrail, router_output_guardrail
from orchestrator.utils import env_bool, env_float

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client():
    return build_openai_client()


class RoutingDecision(BaseModel):
    """Структурированный ответ роутера.

    category маппится на handoff-агента, reason — для логов пользователя.
    """

    category: str = Field(description="router label: robot_info|navigation|swarm_coord|general")
    reason: str | None = Field(default=None, description="why the route was chosen")
    target_robots: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None)


def _model_settings() -> ModelSettings:
    temp = env_float("AGENTS_TEMPERATURE", 0.3)
    top_p = env_float("AGENTS_TOP_P", None)
    max_tokens = env_float("AGENTS_MAX_OUTPUT_TOKENS", None)
    kwargs = {"temperature": temp}
    if top_p is not None:
        kwargs["top_p"] = top_p
    if max_tokens is not None:
        kwargs["max_tokens"] = int(max_tokens)
    return ModelSettings(**kwargs)


def _model_name() -> str:
    return os.getenv("AGENTS_MODEL", "gpt-4o-mini")


def _run_config() -> RunConfig:
    return RunConfig(
        model=_model_name(),
        model_settings=_model_settings(),
        nest_handoff_history=env_bool("AGENTS_NEST_HANDOFF_HISTORY", False),
        tracing_disabled=os.getenv("AGENTS_TRACING_DISABLED", "1") != "0",
    )


def _agent_prompt(agent_name: str) -> str:
    mapping = {
        "Router": prompts.ROUTER_PROMPT,
        "RobotInfo": prompts.ROBOT_INFO_PROMPT,
        "Navigation": prompts.NAVIGATION_PROMPT,
        "Swarm": prompts.SWARM_PROMPT,
        "General": prompts.GENERAL_FALLBACK_PROMPT,
    }
    return mapping.get(agent_name, prompts.GENERAL_FALLBACK_PROMPT)


def _mcp_servers(configs: Iterable[MCPServerConfig]) -> list[MCPServer]:
    servers: list[MCPServer] = []
    for cfg in configs:
        if cfg.transport == "sse":
            if not _HAS_SSE:
                raise RuntimeError(
                    "MCPServerSse is not available in the installed openai-agents version. "
                    "Upgrade to openai-agents>=0.4 or set MISSION_*_TRANSPORT=stdio."
                )
            servers.append(
                MCPServerSse(  # type: ignore[name-defined]
                    params={"url": cfg.url},
                    name=cfg.name,
                )
            )
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
    handoff_agents: list[Agent] = []
    for handoff in cfg.get("handoffs", []):
        handoff_agents.append(
            _build_agent(
                agent_name=handoff.get("name"),
                mcp_configs=handoff.get("mcp_servers", []),
            )
        )

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
    cfg = get_router_config()
    for handoff in cfg.get("handoffs", []):
        if handoff.get("name") == agent_name:
            return handoff.get("mcp_servers", [])
    return []


class AgentsSDKExecutor(AgentHandoffExecutor):
    def __init__(self, stream_collector: Optional[StreamCollector] = None, step_delay: float = 0.05) -> None:
        self._step_delay = step_delay
        self._sc = stream_collector

    async def _record_stream(self, task_id: str, event_type: str, meta: Optional[dict] = None, message: str = ""):
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

    async def execute(self, task_id: str, step, attempt: int) -> HandoffResult:
        if step.agent == "Router":
            agent = _router_agent()
        else:
            agent = _build_agent(step.agent, mcp_configs=_mcp_configs_for(step.agent))
        run_config = _run_config()
        try:
            # Prefer streaming to mirror events to StreamCollector
            run_streamed = getattr(Runner, "run_streamed", None)
            if run_streamed:
                result = run_streamed(agent, input=step.description, run_config=run_config)
                try:
                    async for ev in result.stream_events():  # type: ignore[attr-defined]
                        etype = getattr(ev, "type", "event")
                        item = getattr(ev, "item", None)
                        payload = None
                        if getattr(ev, "name", None):
                            payload = getattr(ev, "name")
                        if item is not None and getattr(item, "output", None):
                            payload = str(getattr(item, "output"))
                        await self._record_stream(
                            task_id,
                            event_type=etype,
                            meta={"agent": step.agent, "attempt": attempt, "sdk_event": etype},
                            message=payload or f"SDK event: {etype}",
                        )
                except Exception:
                    logger.exception("Failed to consume streaming events", extra={"task_id": task_id})

                output = getattr(result, "final_output", None) or getattr(result, "output", None) or None
                message = str(output) if output is not None else ""
                try:
                    parsed = result.final_output_as(RoutingDecision)
                    if parsed:
                        message = parsed.reason or parsed.category or message
                except Exception:
                    pass
                return HandoffResult(success=True, message=message)

            # Fallback to non-streaming run
            result = await Runner.run(agent, step.description, run_config=run_config)
            output = getattr(result, "final_output", None) or result
            message = str(output) if output is not None else ""
            return HandoffResult(success=True, message=message)
        except Exception as exc:
            logger.exception("Agents SDK execution failed", extra={"task_id": task_id, "step_id": step.id})
            return HandoffResult(
                success=False,
                message=str(exc),
                user_message="Шаг не выполнен из-за ошибки агента",
                retryable=False,
            )


__all__ = ["AgentsSDKExecutor"]
