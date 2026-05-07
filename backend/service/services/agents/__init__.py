__all__ = ["DefaultAgentExecutionService", "AgentSessionService", "ModelRoutingService"]


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
    raise AttributeError(name)
