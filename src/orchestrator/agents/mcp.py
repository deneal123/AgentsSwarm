"""MCP server configurations for agents.

This module centralizes how we configure MCP servers for MissionControl,
MissionDispatch, and ROS-MSP.  Two transport modes are supported:

  stdio  (default, local)  — orchestrator spawns the MCP server as a
                              subprocess and communicates via stdin/stdout.
  sse    (Docker)          — MCP server runs in its own container and exposes
                              an SSE/HTTP endpoint; orchestrator connects
                              via MCPServerSse.

Transport is selected per-server via env vars:
  MISSION_CONTROL_TRANSPORT  = stdio | sse   (default: stdio)
  MISSION_DISPATCH_TRANSPORT = stdio | sse   (default: stdio)
  ROS_MSP_TRANSPORT          = stdio | sse   (default: stdio)
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


def _server_config(
    name: str,
    env_prefix: str,
    default_sse_url: str,
    default_command: str,
    default_args: str,
    extra_env: Dict[str, str],
) -> MCPServerConfig:
    transport = os.getenv(f"{env_prefix}_TRANSPORT", "stdio")
    if transport == "sse":
        return MCPServerConfig(
            name=name,
            transport="sse",
            url=os.getenv(f"{env_prefix}_MCP_URL", default_sse_url),
        )
    return MCPServerConfig(
        name=name,
        transport="stdio",
        command=os.getenv(f"{env_prefix}_COMMAND", default_command),
        args=os.getenv(f"{env_prefix}_ARGS", default_args).split(),
        env=extra_env,
    )


def ros_msp_server() -> MCPServerConfig:
    return _server_config(
        name="ros-msp",
        env_prefix="ROS_MSP",
        default_sse_url="http://ros-msp:8000/sse",
        default_command="uv",
        default_args="--directory /opt/ros-mcp-server run server.py",
        extra_env={
            "ROSBRIDGE_IP": os.getenv("ROSBRIDGE_IP", "127.0.0.1"),
            "ROSBRIDGE_PORT": os.getenv("ROSBRIDGE_PORT", "9090"),
        },
    )


def mission_control_server() -> MCPServerConfig:
    return _server_config(
        name="mission-control",
        env_prefix="MISSION_CONTROL",
        default_sse_url="http://mission-control-mcp:8000/sse",
        default_command="python",
        default_args="-m mission_control_mcp.server",
        extra_env={"MISSION_CONTROL_URL": os.getenv("MISSION_CONTROL_URL", "http://localhost:8050")},
    )


def mission_dispatch_server() -> MCPServerConfig:
    return _server_config(
        name="mission-dispatch",
        env_prefix="MISSION_DISPATCH",
        default_sse_url="http://mission-dispatch-mcp:8000/sse",
        default_command="python",
        default_args="-m mission_dispatch_mcp.server",
        extra_env={"MISSION_DISPATCH_URL": os.getenv("MISSION_DISPATCH_URL", "http://localhost:8051")},
    )


__all__ = [
    "MCPServerConfig",
    "ros_msp_server",
    "mission_control_server",
    "mission_dispatch_server",
]
