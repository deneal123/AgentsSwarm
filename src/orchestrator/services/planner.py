"""Planner: builds a deterministic execution plan from a user prompt.

Given a natural-language instruction, produces a list of PlanSteps that the
PlanRunner hands off to specialised agents (Router → RobotInfo / Navigation /
SwarmCoordinator).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple

_ROBOT_ID_RE = re.compile(r"[a-zA-Z]+\d+")
_GOAL_SPLIT_RE = re.compile(r"[.;\n]|\bзатем\b|\bпотом\b|\bthen\b", re.IGNORECASE)


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


def build_plan(prompt: str) -> List[PlanStep]:
    """Two-phase plan builder: analyse → collect context → execute goals.

    Always adds analysis (id=1) and context (id=2) steps, then one execution
    step per extracted goal. Agent type (Navigation/SwarmCoordinator) and tool
    list are chosen by heuristic per goal.
    """
    goals = _extract_goals(prompt) or [prompt.strip()]

    steps: List[PlanStep] = [
        PlanStep(
            id=1,
            description="Анализ запроса и уточнение цели",
            agent="Router",
            meta={
                "expected_outcome": "Уточненная цель и параметры задачи",
                "inputs": {"prompt": prompt},
                "tools": [],
                "depends_on": [],
            },
        ),
        PlanStep(
            id=2,
            description="Получение данных/контекст",
            agent="RobotInfo",
            meta={
                "expected_outcome": "Контекст и данные по доступным роботам",
                "inputs": {"from_step": 1},
                "tools": ["get_fleet_summary", "get_robot_status", "check_robot_health"],
                "depends_on": [1],
                "target_robots": [],
            },
        ),
    ]

    for current_id, goal in enumerate(goals, start=3):
        target_agent, target_robots = _detect_agent(goal)
        tools_for_exec = (
            ["get_idle_robots", "check_robot_health", "submit_navigation_mission",
             "dispatch_mission", "get_mission_status"]
            if target_agent == "SwarmCoordinator"
            else ["get_robot_status", "submit_navigation_mission",
                  "dispatch_mission", "get_mission_status"]
        )
        depends_on = [1, 2] + ([current_id - 1] if current_id > 3 else [])
        steps.append(
            PlanStep(
                id=current_id,
                description=f"Выполнение цели: {goal.strip()}",
                agent=target_agent,
                meta={
                    "expected_outcome": "Выполненная команда/миссия",
                    "inputs": {"from_steps": depends_on, "target_robots": target_robots},
                    "tools": tools_for_exec,
                    "depends_on": depends_on,
                    "target_robots": target_robots,
                },
            )
        )

    return steps


def _detect_agent(prompt: str) -> Tuple[str, List[str]]:
    """Heuristic: pick agent and extract robot ids from a single goal string."""
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
