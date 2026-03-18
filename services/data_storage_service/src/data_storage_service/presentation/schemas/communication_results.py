"""Схемы для эндпоинтов Communication Results (результаты анализа коммуникаций)."""

# Re-export domain models — они являются контрактом API без изменений
from service.models.pydantic.communication import (
    CommunicationResponse as CommunicationResponse,                 # noqa: F401
    CommunicationResultPage as CommunicationResultPage,             # noqa: F401
    CommunicationResultResponse as CommunicationResultResponse,     # noqa: F401
    CommunicationResultSummary as CommunicationResultSummary,       # noqa: F401
    CommunicationSummary as CommunicationSummary,                   # noqa: F401
    TaskCommunicationStats as TaskCommunicationStats,               # noqa: F401
    CommunicationResultCreate as CommunicationResultCreate,         # noqa: F401
)
