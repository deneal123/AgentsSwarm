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


class BotJobStatus(StrEnum):
    """Статусы для Telegram ботов (Jobs)"""

    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    STARTING = "STARTING"


class ServiceType(StrEnum):
    CALENDAR = "CALENDAR"  # Calendar generation job type
    CHAT = "CHAT"  # Agent chat message processing
