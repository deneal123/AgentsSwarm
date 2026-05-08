__all__ = ["MemoryService"]


def __getattr__(name: str):
    if name == "MemoryService":
        from service.services.analytics.application.memory_service import MemoryService

        return MemoryService
    raise AttributeError(name)
