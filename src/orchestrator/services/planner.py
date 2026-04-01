"""Minimal planner scaffold for MissionPlanner-like behavior.

Given a user prompt, build a deterministic list of plan steps
that can be executed by specialized agents. This is a placeholder
until Agent SDK integration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple


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
    """Two-phase plan builder: analyse -> collect context -> execute goals.

    - Always adds analysis (id=1) and context (id=2) steps.
    - Splits complex запрос на подцели, каждая получает свой execution-step.
    - Подбирает агент (Navigation/Swarm) и инструменты по каждой подцели.
    """

    goals = _extract_goals(prompt)
    if not goals:
        goals = [prompt.strip()]

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
                "tools": ["get_robots", "get_robot_status"],
                "depends_on": [1],
                "target_robots": [],
            },
        ),
    ]

    current_id = 3
    for goal in goals:
        target_agent, target_robots = _detect_agent(goal)
        tools_for_exec = ["create_mission", "send_mission"]
        if target_agent == "Swarm":
            tools_for_exec = ["plan_route", "create_mission", "send_mission"]

        depends_on = [1, 2]
        if current_id > 3:
            depends_on.append(current_id - 1)

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
        current_id += 1

    return steps


__all__ = ["PlanStep", "build_plan"]


def _detect_agent(prompt: str) -> Tuple[str, List[str]]:
    """Heuristic to pick target agent and extract robot ids.

    Returns (agent_name, robot_ids).
    """

    lower = prompt.lower()
    robots = _extract_robot_ids(lower)

    swarm_keywords = ["swarm", "несколь", "many", "multi", "group", "team", "ро""й"]
    is_swarm = len(robots) >= 2 or any(k in lower for k in swarm_keywords)

    target_agent = "Swarm" if is_swarm else "Navigation"
    return target_agent, robots


def _extract_robot_ids(text: str) -> List[str]:
    # naive extraction: words with letters + digits (e.g., carter01)
    ids = re.findall(r"[a-zA-Z]+\d+", text)
    seen = set()
    unique = []
    for robot_id in ids:
        if robot_id not in seen:
            seen.add(robot_id)
            unique.append(robot_id)
    return unique


def _extract_goals(prompt: str) -> List[str]:
    # Split by sentence-ending punctuation or sequencing words; keep non-empty trimmed chunks
    parts = re.split(r"[.;\n]|\bзатем\b|\bпотом\b|\bthen\b", prompt, flags=re.IGNORECASE)
    goals = [p.strip() for p in parts if p and p.strip()]
    return goals
