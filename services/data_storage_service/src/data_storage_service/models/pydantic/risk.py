"""
Pydantic schemas for the Rules Marketplace.

Rules are created by admins only. Users create versions and pin active versions.
risk_id is a plain informational string, not a foreign key.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# RULE VERSION SCHEMAS
# ============================================================================


class RuleVersionCreate(BaseModel):
    """Create a new version of an existing rule (any authenticated user)."""

    additional_instructions: str | None = Field(
        None,
        description="LLM prompt / additional instructions that override the base rule behaviour",
    )
    patterns: dict[str, str] = Field(
        default_factory=dict,
        description="Regex patterns for simple/combine rules, e.g. {'key': 'regex'}",
    )
    change_description: str | None = Field(
        None, description="Short human-readable summary of what changed"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra metadata")


class RuleVersionResponse(BaseModel):
    """Rule version details returned by the API."""

    id: UUID
    rule_id: UUID = Field(description="Internal UUID of the parent rule")
    version_number: int
    additional_instructions: str | None
    patterns: dict[str, str] = Field(default_factory=dict)
    change_description: str | None
    created_by_user_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# RULE SCHEMAS
# ============================================================================


class RuleCreate(BaseModel):
    """Create a new rule in the marketplace (admin only)."""

    rule_id: str = Field(
        ...,
        max_length=100,
        description="Unique human-readable rule identifier, e.g. '1.1-ОР'",
    )
    risk_id: str | None = Field(
        None,
        max_length=100,
        description="Informational risk code, e.g. '1.1' — display only, no FK",
    )
    risk_category: str | None = Field(None, max_length=255, description="Risk category label")
    name: str = Field(..., max_length=500, description="Rule name")
    description: str | None = Field(None, description="Rule description")
    consequences: str | None = Field(None, description="Consequences of the risk")
    levels: str | None = Field(None, description="Risk levels")
    measures: str | None = Field(None, description="Preventive measures")
    additional_information: str | None = Field(None, description="Additional information")
    rule_type: str = Field(
        ..., max_length=50, description="Rule type: 'simple' | 'llm' | 'combined'"
    )
    risk_present_if: int = Field(
        1, description="Model output value that signals the risk is present (1 or 0)"
    )
    product_types: list[str] = Field(
        default_factory=list, description="Applicable products, e.g. ['кредит', 'вклад']"
    )
    channel_types: list[str] = Field(
        default_factory=list, description="Applicable channels, e.g. ['sms', 'push', 'all']"
    )
    initial_instructions: str | None = Field(
        None, description="LLM instructions for version 1 (created automatically on rule creation)"
    )
    initial_patterns: dict[str, str] = Field(
        default_factory=dict,
        description="Regex patterns for version 1 (for simple/combine rules)",
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RuleUpdate(BaseModel):
    """Update static fields of an existing rule (admin only)."""

    name: str | None = Field(None, max_length=500)
    risk_id: str | None = Field(None, max_length=100, description="Informational risk code")
    risk_category: str | None = Field(None, max_length=255)
    description: str | None = None
    consequences: str | None = None
    levels: str | None = None
    measures: str | None = None
    additional_information: str | None = None
    rule_type: str | None = Field(None, max_length=50)
    risk_present_if: int | None = None
    product_types: list[str] | None = None
    channel_types: list[str] | None = None
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None


class RuleResponse(BaseModel):
    """Full rule details, including all versions."""

    id: UUID
    rule_id: str = Field(description="Unique human-readable identifier, e.g. '1.1-ОР'")
    risk_id: str | None = Field(description="Informational risk code (display only)")
    risk_category: str | None
    name: str
    description: str | None
    consequences: str | None
    levels: str | None
    measures: str | None
    additional_information: str | None
    rule_type: str
    risk_present_if: int
    product_types: list[str]
    channel_types: list[str]
    is_active: bool
    current_version: int = Field(description="Latest version number created for this rule")
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime | None
    versions: list[RuleVersionResponse] = Field(
        default_factory=list, description="All versions of this rule"
    )

    model_config = ConfigDict(from_attributes=True)


class RuleListResponse(BaseModel):
    """Lightweight rule entry for list views (no versions included)."""

    id: UUID
    rule_id: str
    risk_id: str | None
    risk_category: str | None
    name: str
    rule_type: str
    product_types: list[str]
    channel_types: list[str]
    is_active: bool
    current_version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# USER RULE PREFERENCE SCHEMAS
# ============================================================================


class UserRulePreferenceSet(BaseModel):
    """Request body for pinning an active version of a rule."""

    pinned_version_number: int | None = Field(
        None,
        description=(
            "Version number to pin as active. "
            "Pass null to reset to 'latest version' behaviour."
        ),
    )


class UserRulePreferenceResponse(BaseModel):
    """Response after updating user's active version preference."""

    rule_id: str = Field(description="Human-readable rule identifier")
    rule_uuid: UUID = Field(description="Internal UUID of the rule")
    pinned_version_number: int | None = Field(
        description="Pinned version; null means 'use latest'"
    )
    effective_version_number: int = Field(
        description="The version that will actually be used in pipeline/playground runs"
    )


class UserRuleSnapshotEntry(BaseModel):
    """One rule + its resolved active version for the current user."""

    rule_id: str
    rule_uuid: UUID
    name: str
    rule_type: str
    risk_present_if: int
    product_types: list[str]
    channel_types: list[str]
    active_version_number: int
    additional_instructions: str | None
    patterns: dict[str, str] = Field(default_factory=dict)


class UserRulesSnapshot(BaseModel):
    """Full snapshot of user's rule set used when launching pipeline/playground."""

    rules: list[UserRuleSnapshotEntry]
    total: int


# ============================================================================
# PIPELINE CONFIG SCHEMAS
# ============================================================================


class PipelineConfigCreate(BaseModel):
    """Create a new pipeline config snapshot (admin only)."""

    config_data: dict[str, Any] = Field(..., description="Full config.yaml snapshot")
    change_description: str | None = Field(None, description="Description of changes")
    is_active: bool = Field(False, description="Activate this version immediately")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class PipelineConfigUpdate(BaseModel):
    """Update pipeline config (admin only)."""

    is_active: bool | None = None
    metadata: dict[str, Any] | None = None


class PipelineConfigResponse(BaseModel):
    """Pipeline config response."""

    id: UUID
    version_number: int
    config_data: dict[str, Any]
    change_description: str | None
    is_active: bool
    created_by_user_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

