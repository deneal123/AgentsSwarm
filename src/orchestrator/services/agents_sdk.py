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
from orchestrator.services.map_analyst import get_map_context
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
    "MapAnalyst": prompts.MAP_ANALYST_PROMPT,
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
        if step.agent == "MapAnalyst":
            return await self._run_map_analyst(task_id, step)

        agent = _router_agent() if step.agent == "Router" else _build_agent(
            step.agent, mcp_configs=_mcp_configs_for(step.agent)
        )
        run_config = _run_config()

        async with contextlib.AsyncExitStack() as stack:
            for server in self._collect_mcp_servers(agent):
                await stack.enter_async_context(server)

            return await self._run_agent(task_id, step, attempt, agent, run_config)

    async def _run_map_analyst(self, task_id: str, step) -> HandoffResult:
        import base64
        import json

        await self._record_stream(task_id, "map_analyst_start", message="Fetching map...")
        try:
            map_ctx = await get_map_context()
        except Exception:
            logger.exception("Failed to fetch map", extra={"task_id": task_id})
            return HandoffResult(success=True, message="")

        if map_ctx is None:
            return HandoffResult(success=True, message="")

        meta = map_ctx.metadata
        mime = "image/png" if map_ctx.image_bytes[:4] == b"\x89PNG" else "image/jpeg"
        b64_map = base64.b64encode(map_ctx.image_bytes).decode()

        await self._record_stream(
            task_id, "map_analyst_candidates",
            meta={"map_id": meta.get("map_id"), "resolution": meta.get("resolution")},
            message="Map fetched, generating route candidates...",
        )

        # ── Phase 1: Agent proposes 3 route candidates ──────────────────────
        candidates_json: dict | None = None
        try:
            mcp_configs = _mcp_configs_for("Navigation")
            agent = _build_agent("MapAnalyst", mcp_configs=mcp_configs)

            agent_input = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"ЗАДАЧА: {step.meta.get('task_description', step.description)}\n\n"
                                f"МЕТАДАТА КАРТЫ:\n"
                                f"- map_id: {meta.get('map_id', 'unknown')}\n"
                                f"- resolution: {meta.get('resolution', '?')} m/px\n"
                                f"- x_offset: {meta.get('x_offset', '?')} m\n"
                                f"- y_offset: {meta.get('y_offset', '?')} m\n"
                                f"- safety_distance: {meta.get('safety_distance', 0.45)} m\n\n"
                                "Проанализируй карту и предложи 3 варианта маршрута согласно инструкции."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64_map}"}},
                    ],
                }
            ]

            async with contextlib.AsyncExitStack() as stack:
                for server in self._collect_mcp_servers(agent):
                    await stack.enter_async_context(server)
                result = await Runner.run(agent, agent_input, run_config=_run_config())

            raw = str(getattr(result, "final_output", None) or result)
            # Strip possible markdown fences
            import re as _re
            raw = _re.sub(r"^```[a-z]*\n?", "", raw.strip()).rstrip("`").strip()
            candidates_json = json.loads(raw)
        except Exception:
            logger.exception("MapAnalyst candidate generation failed", extra={"task_id": task_id})
            return HandoffResult(success=True, message="")

        candidates = candidates_json.get("candidates", [])
        if not candidates:
            return HandoffResult(success=True, message="")

        await self._record_stream(
            task_id, "map_analyst_visualize",
            meta={"num_candidates": len(candidates)},
            message=f"Visualizing {len(candidates)} route candidates...",
        )

        # ── Phase 2: Visualize each candidate via Mission Control API ────────
        import os
        import httpx

        base_url = os.getenv("MISSION_CONTROL_URL", "http://localhost:8050").rstrip("/")
        visualizations: list[tuple[str, bytes]] = []  # (candidate_name, png_bytes)

        async with httpx.AsyncClient(timeout=20.0) as http:
            for candidate in candidates:
                waypoints = candidate.get("waypoints", [])
                if not waypoints:
                    continue
                try:
                    resp = await http.post(
                        f"{base_url}/api/v1/visualize_route",
                        json={"route": waypoints, "solver": "CPU_DIJKSTRA"},
                    )
                    resp.raise_for_status()
                    if resp.content:
                        visualizations.append((candidate["name"], resp.content))
                except Exception:
                    logger.warning(
                        "visualize_route failed for candidate %s", candidate.get("name"),
                        extra={"task_id": task_id},
                    )

        if not visualizations:
            best = candidates[0]
            return HandoffResult(
                success=True,
                message=self._format_map_result(candidates_json, best, reason="visualization unavailable"),
            )

        await self._record_stream(
            task_id, "map_analyst_compare",
            meta={"num_visualized": len(visualizations)},
            message=f"Comparing {len(visualizations)} route visualizations...",
        )

        # ── Phase 3: Vision LLM compares all route images ────────────────────
        best_candidate, reason = await self._compare_routes(
            visualizations, candidates, candidates_json.get("target", {})
        )

        await self._record_stream(
            task_id, "map_analyst_done",
            meta={"winner": best_candidate.get("name"), "reason": reason},
            message=f"Best route selected: '{best_candidate.get('name')}' — {reason}",
        )

        return HandoffResult(
            success=True,
            message=self._format_map_result(candidates_json, best_candidate, reason),
        )

    async def _compare_routes(
        self,
        visualizations: list[tuple[str, bytes]],
        candidates: list[dict],
        target: dict,
    ) -> tuple[dict, str]:
        import base64

        client = _client()
        model = _model_name()

        # Build vision message with all route images
        content: list[dict] = [
            {
                "type": "text",
                "text": (
                    "You are evaluating robot navigation routes. "
                    f"Target destination: x={target.get('x', '?')}, y={target.get('y', '?')}.\n\n"
                    "The following images show different route visualizations on the same map. "
                    "Each image shows waypoints and the planned path.\n\n"
                    "Evaluate each route for:\n"
                    "1. Path efficiency (shorter is better)\n"
                    "2. Safety margin from walls and obstacles\n"
                    "3. Smoothness (fewer sharp turns)\n"
                    "4. Risk of getting stuck in narrow passages\n\n"
                    f"Routes being compared: {', '.join(name for name, _ in visualizations)}\n\n"
                    "Reply with JSON only: "
                    '{"winner": "<route_name>", "reason": "<one sentence why>"}'
                ),
            }
        ]

        for name, png_bytes in visualizations:
            b64 = base64.b64encode(png_bytes).decode()
            content.append({"type": "text", "text": f"Route: {name}"})
            content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})

        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": content}],
                max_tokens=200,
                temperature=0,
            )
            import json, re as _re
            raw = (resp.choices[0].message.content or "").strip()
            raw = _re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
            decision = json.loads(raw)
            winner_name = decision.get("winner", "")
            reason = decision.get("reason", "")
            for c in candidates:
                if c.get("name") == winner_name:
                    return c, reason
        except Exception:
            logger.exception("Route comparison vision call failed")

        return candidates[0], "fallback to first candidate"

    @staticmethod
    def _format_map_result(candidates_json: dict, best: dict, reason: str) -> str:
        target = candidates_json.get("target", {})
        warnings = candidates_json.get("warnings", [])
        waypoints = best.get("waypoints", [])
        wp_str = ", ".join(f"({w['x']:.2f}, {w['y']:.2f})" for w in waypoints)

        lines = [
            "=== MAP ANALYSIS RESULT ===",
            f"TARGET: x={target.get('x', '?')}, y={target.get('y', '?')}",
            f"BEST ROUTE: {best.get('name')} — {reason}",
            # Waypoints are intermediate + destination only (NOT robot start position).
            # Navigation agent prepends robot's actual current position from get_robot_status.
            f"WAYPOINTS (intermediate + destination, excluding robot start): [{wp_str}]",
            f"RATIONALE: {best.get('rationale', '')}",
        ]
        if warnings:
            lines.append(f"WARNINGS: {'; '.join(warnings)}")

        lines += [
            "",
            "OTHER CANDIDATES:",
        ]
        for c in candidates_json.get("candidates", []):
            if c.get("name") != best.get("name"):
                wp = ", ".join(f"({w['x']:.2f}, {w['y']:.2f})" for w in c.get("waypoints", []))
                lines.append(f"  • {c['name']}: [{wp}] — {c.get('rationale', '')}")

        lines.append("===========================")
        return "\n".join(lines)

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
