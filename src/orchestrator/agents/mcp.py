"""MCP server configurations for agents.

This module centralizes how we configure MCP servers for MissionControl and
MissionDispatch.  Two transport modes are supported:

  stdio  (default, local)  — orchestrator spawns the MCP server as a
                              subprocess and communicates via stdin/stdout.
  sse    (Docker)          — MCP server runs in its own container and exposes
                              an SSE/HTTP endpoint; orchestrator connects
                              via MCPServerSse.

Transport is selected per-server via env vars:
  MISSION_CONTROL_TRANSPORT  = stdio | sse   (default: stdio)
  MISSION_DISPATCH_TRANSPORT = stdio | sse   (default: stdio)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class MCPServerConfig:
    name: str
    transport: str = "stdio"   # "stdio" | "sse"

    # --- stdio fields ---
    command: str = ""
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)

    # --- sse fields ---
    url: str = ""


def ros_msp_server() -> MCPServerConfig:
    # ROS-MSP is only available as a local subprocess — no SSE container yet.
    return MCPServerConfig(
        name="ros-msp",
        transport="stdio",
        command=os.getenv("ROS_MSP_COMMAND", "uv"),
        args=os.getenv("ROS_MSP_ARGS", "--directory /opt/ros-mcp-server run server.py").split(),
        env={},
    )


def mission_control_server() -> MCPServerConfig:
    transport = os.getenv("MISSION_CONTROL_TRANSPORT", "stdio")
    if transport == "sse":
        return MCPServerConfig(
            name="mission-control",
            transport="sse",
            url=os.getenv(
                "MISSION_CONTROL_MCP_URL",
                "http://mission-control-mcp:8000/sse",
            ),
        )
    return MCPServerConfig(
        name="mission-control",
        transport="stdio",
        command=os.getenv("MISSION_CONTROL_COMMAND", "python"),
        args=os.getenv(
            "MISSION_CONTROL_ARGS", "-m mission_control_mcp.server"
        ).split(),
        env={"MISSION_CONTROL_URL": os.getenv("MISSION_CONTROL_URL", "http://localhost:8050")},
    )


def mission_dispatch_server() -> MCPServerConfig:
    transport = os.getenv("MISSION_DISPATCH_TRANSPORT", "stdio")
    if transport == "sse":
        return MCPServerConfig(
            name="mission-dispatch",
            transport="sse",
            url=os.getenv(
                "MISSION_DISPATCH_MCP_URL",
                "http://mission-dispatch-mcp:8000/sse",
            ),
        )
    return MCPServerConfig(
        name="mission-dispatch",
        transport="stdio",
        command=os.getenv("MISSION_DISPATCH_COMMAND", "python"),
        args=os.getenv(
            "MISSION_DISPATCH_ARGS", "-m mission_dispatch_mcp.server"
        ).split(),
        env={"MISSION_DISPATCH_URL": os.getenv("MISSION_DISPATCH_URL", "http://localhost:8051")},
    )


__all__ = [
    "MCPServerConfig",
    "ros_msp_server",
    "mission_control_server",
    "mission_dispatch_server",
]
