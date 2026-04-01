"""MCP server configurations for agents.

This module centralizes how we configure MCP stdio servers for RosMSP,
MissionControl, and MissionDispatch. Actual agent wiring will import these
configs and pass them to the Agents SDK.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class MCPServerConfig:
    name: str
    command: str
    args: List[str]
    env: Dict[str, str] = field(default_factory=dict)


def ros_msp_server() -> MCPServerConfig:
    return MCPServerConfig(
        name="ros-msp",
        command=os.getenv("ROS_MSP_COMMAND", "uv"),
        args=os.getenv("ROS_MSP_ARGS", "--directory /opt/ros-mcp-server run server.py").split(),
        env={},
    )


def mission_control_server() -> MCPServerConfig:
    return MCPServerConfig(
        name="mission-control",
        command=os.getenv("MISSION_CONTROL_COMMAND", "python"),
        args=os.getenv("MISSION_CONTROL_ARGS", "-m mission_control_mcp.server").split(),
        env={"MISSION_CONTROL_URL": os.getenv("MISSION_CONTROL_URL", "http://localhost:8050")},
    )


def mission_dispatch_server() -> MCPServerConfig:
    return MCPServerConfig(
        name="mission-dispatch",
        command=os.getenv("MISSION_DISPATCH_COMMAND", "python"),
        args=os.getenv("MISSION_DISPATCH_ARGS", "-m mission_dispatch_mcp.server").split(),
        env={"MISSION_DISPATCH_URL": os.getenv("MISSION_DISPATCH_URL", "http://localhost:8051")},
    )


__all__ = [
    "MCPServerConfig",
    "ros_msp_server",
    "mission_control_server",
    "mission_dispatch_server",
]
