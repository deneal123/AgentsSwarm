from __future__ import annotations

from typing import TYPE_CHECKING

from orchestrator.utils.env import env_bool

if TYPE_CHECKING:
    from orchestrator.services.plan_runner import AgentHandoffExecutor, SimulatedAgentExecutor
    from orchestrator.services.streaming import StreamCollector


class AgentExecutorFactory:
    @staticmethod
    def create(stream_collector: "StreamCollector", step_delay: float) -> "AgentHandoffExecutor":
        from orchestrator.services.plan_runner import SimulatedAgentExecutor

        if env_bool("AGENTS_USE_SDK", default=False):
            try:
                from orchestrator.services.agents_sdk import AgentsSDKExecutor

                return AgentsSDKExecutor(stream_collector=stream_collector)
            except Exception:
                return SimulatedAgentExecutor(latency=step_delay)
        return SimulatedAgentExecutor(latency=step_delay)


__all__ = ["AgentExecutorFactory"]
