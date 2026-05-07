"""Planner: builds an execution plan from a user prompt via LLM.

Primary path: calls the configured LLM with a structured JSON schema to extract
goals, agent assignments, and target robots from the prompt.
Fallback: regex heuristics if the LLM call fails or returns nothing.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Tuple

from pydantic import BaseModel

logger = logging.getLogger(__name__)

_ROBOT_ID_RE = re.compile(r"[a-zA-Z]+\d+")
_GOAL_SPLIT_RE = re.compile(r"(?<!\d)\.(?!\d)|;|\n|\bзатем\b|\bпотом\b|\bthen\b", re.IGNORECASE)

_PLANNER_SYSTEM_PROMPT = """\
You are a robot fleet planner. Given a user request, extract the list of execution goals.

Return JSON only (no markdown) matching this schema:
{"goals": [{"description": "...", "agent": "...", "target_robots": ["robotId"]}]}

Agent selection rules:
- "Navigation"       — single-robot movement, navigation, positioning, docking/undocking,
                       OR canceling missions for a single robot (cancel, stop, abort)
- "SwarmCoordinator" — multi-robot or swarm tasks, canceling missions for multiple robots
- "RobotInfo"        — status queries, health checks, fleet summaries, mission history
- "General"          — greetings, help questions, anything that requires no robot action

Important:
- Do NOT split coordinates, IDs, or values across multiple goals.
- One goal = one distinct user action.
- target_robots: robot IDs explicitly mentioned (e.g. "carter01"), else [].
- "Cancel/stop/abort missions for robot X" → Navigation (it has cancel_active_missions tool).
"""


@dataclass
class PlanStep:
    id: int
    description: str
    agent: str
    status: str = "pending"
    meta: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "agent": self.agent,
            "status": self.status,
            "meta": self.meta,
        }


class _GoalItem(BaseModel):
    description: str
    agent: str
    target_robots: list[str] = []


class _LLMPlan(BaseModel):
    goals: list[_GoalItem]


@lru_cache(maxsize=1)
def _get_openai_client():
    from orchestrator.services.openai_client import build_openai_client
    return build_openai_client()


async def _build_plan_llm(prompt: str) -> list[_GoalItem] | None:
    try:
        client = _get_openai_client()
        model = os.getenv("AGENTS_MODEL", "gpt-4o-mini")
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        raw = (resp.choices[0].message.content or "").strip()
        # strip possible markdown code fences
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
        plan = _LLMPlan.model_validate_json(raw)
        if plan.goals:
            return plan.goals
    except Exception:
        logger.exception("LLM planner failed, falling back to heuristic")
    return None


def _build_plan_heuristic(prompt: str) -> list[tuple[str, str, list[str]]]:
    goals = _extract_goals(prompt) or [prompt.strip()]
    return [(g.strip(), *_detect_agent(g)) for g in goals]


async def build_plan(prompt: str) -> List[PlanStep]:
    """Build execution plan: LLM-primary, heuristic fallback."""
    llm_goals = await _build_plan_llm(prompt)

    if llm_goals:
        goal_tuples: list[tuple[str, str, list[str]]] = [
            (g.description, g.agent, g.target_robots) for g in llm_goals
        ]
    else:
        goal_tuples = _build_plan_heuristic(prompt)

    # MapAnalyst is only useful for actual movement — skip it for cancel/status tasks.
    _MOVEMENT_WORDS = {"отправ", "перем", "навигац", "move", "go", "send", "navigat", "поед", "доед"}
    _CANCEL_WORDS = {"отмен", "cancel", "stop", "abort", "останов", "прекрат"}

    def _needs_map_for(description: str, agent: str) -> bool:
        if agent not in {"Navigation", "SwarmCoordinator"}:
            return False
        desc_lower = description.lower()
        # Cancel/stop/abort tasks don't need map analysis.
        if any(w in desc_lower for w in _CANCEL_WORDS):
            return False
        # All other Navigation/Swarm tasks default to needing the map.
        return True

    needs_map = any(_needs_map_for(desc, agent) for desc, agent, _ in goal_tuples)

    steps: List[PlanStep] = []
    current_id = 1

    if needs_map:
        nav_goals = [desc for desc, agent, _ in goal_tuples if agent in {"Navigation", "SwarmCoordinator"}]
        steps.append(
            PlanStep(
                id=current_id,
                description="Анализ карты окружения для навигации",
                agent="MapAnalyst",
                meta={
                    "expected_outcome": "Целевые координаты, рекомендуемые waypoints, препятствия на пути",
                    "inputs": {"prompt": prompt},
                    "tools": [],
                    "depends_on": [],
                    "task_description": " | ".join(nav_goals),
                },
            )
        )
        current_id += 1

    map_step_ids = [s.id for s in steps]

    for description, agent, target_robots in goal_tuples:
        tools_for_exec = (
            ["get_idle_robots", "check_robot_health", "cancel_active_missions",
             "dispatch_mission", "get_mission_status"]
            if agent == "SwarmCoordinator"
            else ["get_robot_status", "cancel_active_missions", "cancel_mission",
                  "dispatch_mission", "get_mission_status"]
        )
        depends_on = map_step_ids + ([current_id - 1] if current_id > (map_step_ids[-1] + 1 if map_step_ids else 1) else [])
        steps.append(
            PlanStep(
                id=current_id,
                description=description,
                agent=agent,
                meta={
                    "expected_outcome": "Выполненная команда/миссия",
                    "inputs": {"prompt": prompt, "target_robots": target_robots},
                    "tools": tools_for_exec,
                    "depends_on": depends_on,
                    "target_robots": target_robots,
                },
            )
        )
        current_id += 1

    return steps


def _detect_agent(prompt: str) -> Tuple[str, List[str]]:
    lower = prompt.lower()
    robots = _extract_robot_ids(lower)
    swarm_keywords = ["swarm", "несколь", "many", "multi", "group", "team", "рой"]
    is_swarm = len(robots) >= 2 or any(k in lower for k in swarm_keywords)
    return ("SwarmCoordinator" if is_swarm else "Navigation"), robots


def _extract_robot_ids(text: str) -> List[str]:
    return list(dict.fromkeys(_ROBOT_ID_RE.findall(text)))


def _extract_goals(prompt: str) -> List[str]:
    parts = _GOAL_SPLIT_RE.split(prompt)
    return [p.strip() for p in parts if p and p.strip()]


__all__ = ["PlanStep", "build_plan"]
