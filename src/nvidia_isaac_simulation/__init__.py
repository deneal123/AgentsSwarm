"""Minimal placeholder for NVIDIA ISAAC simulation service."""

from nvidia_isaac_simulation.config.config import settings

__version__ = settings.version

def run_simulation_placeholder() -> str:
    return "ISAAC placeholder running"
