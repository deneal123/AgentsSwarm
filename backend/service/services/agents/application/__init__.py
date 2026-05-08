__all__ = [
    "DefaultAgentExecutionService",
    "AgentSessionService",
    "ModelRoutingService",
    "Orchestrator",
    "AgentProcessor",
]


def __getattr__(name: str):
    if name == "DefaultAgentExecutionService":
        from service.services.agents.application.agent_execution_service import DefaultAgentExecutionService
        return DefaultAgentExecutionService
    if name == "AgentSessionService":
        from service.services.agents.application.agent_session_service import AgentSessionService
        return AgentSessionService
    if name == "ModelRoutingService":
        from service.services.agents.application.model_routing_service import ModelRoutingService
        return ModelRoutingService
    if name == "Orchestrator":
        from service.services.agents.application.orchestrator import Orchestrator
        return Orchestrator
    if name == "AgentProcessor":
        from service.services.agents.application.processor import AgentProcessor
        return AgentProcessor
    raise AttributeError(name)
