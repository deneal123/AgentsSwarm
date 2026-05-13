"""Router agent placeholder wiring.

Once the OpenAI Agents SDK is plugged in, this module will instantiate the
router with handoffs to specialized agents.
"""

from __future__ import annotations

from orchestrator.agents import prompts
from orchestrator.agents.mcp import (
    mission_control_server,
    mission_dispatch_server,
    ros_msp_server,
)

# Placeholder structures; replace with Agents SDK types when available.
HANDOFF_LABELS = {
    "robot_info":  "RobotInfo",
    "navigation":  "Navigation",
    "charging":    "Charging",
    "patrol":      "Patrol",
    "inspection":  "Inspection",
    "fleet_ops":   "FleetOps",
    "swarm_coord": "SwarmCoordinator",
    "general":     "General",
}


def get_router_config() -> dict:
    """Return a router config dict describing handoffs and prompts."""
    return {
        "name": "Router",
        "instructions": prompts.ROUTER_PROMPT,
        "handoffs": [
            {
                "name": HANDOFF_LABELS["robot_info"],
                "instructions": prompts.ROBOT_INFO_PROMPT,
                "mcp_servers": [ros_msp_server(), mission_dispatch_server()],
            },
            {
                "name": HANDOFF_LABELS["navigation"],
                "instructions": prompts.NAVIGATION_PROMPT,
                "mcp_servers": [mission_control_server(), mission_dispatch_server()],
            },
            {
                "name": HANDOFF_LABELS["charging"],
                "instructions": prompts.CHARGING_PROMPT,
                "mcp_servers": [mission_control_server(), mission_dispatch_server()],
            },
            {
                "name": HANDOFF_LABELS["patrol"],
                "instructions": prompts.PATROL_PROMPT,
                "mcp_servers": [mission_control_server(), mission_dispatch_server()],
            },
            {
                "name": HANDOFF_LABELS["inspection"],
                "instructions": prompts.INSPECTION_PROMPT,
                "mcp_servers": [mission_control_server(), mission_dispatch_server()],
            },
            {
                "name": HANDOFF_LABELS["fleet_ops"],
                "instructions": prompts.FLEET_OPS_PROMPT,
                "mcp_servers": [mission_control_server(), mission_dispatch_server()],
            },
            {
                "name": HANDOFF_LABELS["swarm_coord"],
                "instructions": prompts.SWARM_PROMPT,
                "mcp_servers": [ros_msp_server(), mission_control_server(), mission_dispatch_server()],
            },
            {
                "name": HANDOFF_LABELS["general"],
                "instructions": prompts.GENERAL_FALLBACK_PROMPT,
                "mcp_servers": [],
            },
        ],
        "router_tests": {
            "robot_info": [
                "Покажи статус carter01",
                "Сколько роботов сейчас онлайн",
                "Какая батарея у carter01?",
            ],
            "navigation": [
                "Отправь carter01 на склад А",
                "Перемести робота в точку (1,2)",
                "Перемести carter01 в случайные координаты",
                "Отправь carter01 в произвольную точку",
            ],
            "charging": [
                "Зарядить carter01",
                "Отправь carter01 на зарядку",
                "Отстыкуй carter01 от базы",
                "Зарядить всех роботов с низким зарядом",
            ],
            "patrol": [
                "Патрулировать периметр склада",
                "Запусти обход зоны на carter01",
                "Циклический маршрут по четырём точкам",
                "Carter01 должен объезжать зону каждые 10 минут",
            ],
            "inspection": [
                "Что видит камера carter01?",
                "Найди AprilTag ID=3",
                "Какие объекты обнаружил carter01?",
                "Подъедь к ящику который видит carter01",
            ],
            "fleet_ops": [
                "Отмени все миссии",
                "Зарядить весь флот",
                "Отчёт по флоту",
                "Диагностика системы",
                "Сколько миссий завершилось сегодня?",
            ],
            "swarm_coord": [
                "Организуй встречу carter01 и carter02 в центре",
                "Пусть три робота обследуют зону",
                "Отправь рой роботов к цели",
            ],
            "general": [
                "Привет",
                "Что ты умеешь?",
            ],
        },
    }


__all__ = ["get_router_config"]
