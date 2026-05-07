__all__ = ["ChatApplicationService"]


def __getattr__(name: str):
    if name == "ChatApplicationService":
        from service.services.chat.application.chat_application_service import ChatApplicationService

        return ChatApplicationService
    raise AttributeError(name)
