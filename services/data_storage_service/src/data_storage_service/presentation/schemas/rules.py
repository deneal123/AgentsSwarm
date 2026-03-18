"""Схемы для эндпоинтов маркетплейса правил (Rules Marketplace).

Запросы определены здесь, ответы re-exported из domain-моделей.
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Re-export domain response/request models (источник правды — service.models)
# ---------------------------------------------------------------------------
from service.models.pydantic.risk import (
    RuleCreate as RuleCreate,                                   # noqa: F401
    RuleUpdate as RuleUpdate,                                   # noqa: F401
    RuleResponse as RuleResponse,                               # noqa: F401
    RuleListResponse as RuleListResponse,                       # noqa: F401
    RuleVersionCreate as RuleVersionCreate,                     # noqa: F401
    RuleVersionResponse as RuleVersionResponse,                 # noqa: F401
    UserRulePreferenceSet as UserRulePreferenceSet,             # noqa: F401
    UserRulePreferenceResponse as UserRulePreferenceResponse,   # noqa: F401
    UserRulesSnapshot as UserRulesSnapshot,                     # noqa: F401
    UserRuleSnapshotEntry as UserRuleSnapshotEntry,             # noqa: F401
)
from service.models.pydantic.risk import (
    PipelineConfigCreate as PipelineConfigCreate,               # noqa: F401
    PipelineConfigResponse as PipelineConfigResponse,           # noqa: F401
)


# ---------------------------------------------------------------------------
# Presentation-only response schemas
# ---------------------------------------------------------------------------


class RulesImportStats(BaseModel):
    """Статистика импорта правил из TOML-файла."""

    status: str = "completed"
    stats: dict[str, Any] = Field(default_factory=dict)
