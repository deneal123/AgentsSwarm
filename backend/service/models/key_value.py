from enum import StrEnum


class UserTypes(StrEnum):
    REGISTERED = "REGISTERED"


class SessionStatus(StrEnum):
    ACTIVATED = "ACTIVATED"
    WAITING = "WAITING"
    EXPIRED = "EXPIRED"


class ProcessingStatus(StrEnum):
    NEW = "NEW"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class ServiceType(StrEnum):
    CHAT = "CHAT"  # Agent chat message processing
