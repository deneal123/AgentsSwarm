__all__ = ["chat_service", "agent_file_bridge"]


def __getattr__(name: str):
    if name == "chat_service":
        from service.chat.domain import chat_service

        return chat_service
    if name == "agent_file_bridge":
        from service.agents.application import agent_file_bridge

        return agent_file_bridge
    raise AttributeError(name)
