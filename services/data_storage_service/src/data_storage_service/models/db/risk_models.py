"""
Rule models for Pushi — Rules Marketplace.

Roles:
  - Admin creates rules (fixed marketplace catalogue, e.g. 11 rules with unique rule_id).
  - Any authenticated user can create new versions of any existing rule.
  - Each user independently pins the active version per rule via UserRulePreference.
    pinned_version_number = NULL  →  use the latest version created by that user;
                                     if none exist → use the globally latest version.

risk_id is a plain informational string field (e.g. '3.4') — NOT a foreign key,
just descriptive metadata alongside name/description.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from service.models.db.base_db_model import Base
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from service.models.db.communication_models import CommunicationResult
    from service.models.db.user_models import User


class Rule(Base):
    """A rule in the marketplace catalogue — created by admin only.

    rule_id  — unique human-readable identifier chosen by admin, e.g. '1.1-ОР'.
    risk_id  — informational label only (e.g. '1.1'), NOT a foreign key.
    current_version — incremented each time a new version is created (any user).
    """

    __tablename__ = "rules"
    __table_args__ = {"schema": "profile"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4, comment="Internal UUID"
    )
    rule_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Admin-defined unique rule identifier, e.g. '1.1-ОР'",
    )
    # Informational fields — no FK, just descriptive metadata
    risk_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Informational risk code, e.g. '1.1' (display only, no FK)",
    )
    risk_category: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Risk category label"
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False, comment="Rule name")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Rule description")
    consequences: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Consequences of the risk"
    )
    levels: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Risk levels")
    measures: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Preventive measures")
    additional_information: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Additional information"
    )
    rule_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="Rule type: simple | llm | combined"
    )
    risk_present_if: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, comment="Expected model output to flag risk: 1 or 0"
    )
    product_types: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
        comment="Applicable product types, e.g. ['кредит', 'вклад']",
    )
    channel_types: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
        comment="Applicable channel types, e.g. ['sms', 'push', 'all']",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True, comment="Soft-delete flag"
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Admin who created the rule",
    )
    current_version: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, comment="Highest version number created so far"
    )
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}", comment="Additional metadata"
    )

    # Relationships
    rule_versions: Mapped[list["RuleVersion"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan", lazy="selectin"
    )
    user_preferences: Mapped[list["UserRulePreference"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan", lazy="noload"
    )
    communication_results: Mapped[list["CommunicationResult"]] = relationship(
        back_populates="rule", lazy="selectin"
    )


class RuleVersion(Base):
    """A versioned snapshot of a rule's prompt/instructions.

    Any authenticated user can create a new version.
    version_number is unique per rule (global counter, not per-user).
    """

    __tablename__ = "rule_versions"
    __table_args__ = (
        UniqueConstraint("rule_id", "version_number", name="uq_rule_version"),
        {"schema": "profile"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4, comment="Unique version identifier"
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profile.rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to rule",
    )
    version_number: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment="Sequential version number for this rule"
    )
    additional_instructions: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="LLM prompt / additional instructions for this version"
    )
    patterns: Mapped[dict[str, str]] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
        comment="Regex patterns dict for simple/combine rules, e.g. {'key': 'regex'}",
    )
    change_description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="What changed in this version"
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who created this version",
    )
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}", comment="Additional metadata"
    )

    # Relationships
    rule: Mapped["Rule"] = relationship(back_populates="rule_versions", lazy="selectin")


class UserRulePreference(Base):
    """Per-user active version preference for a rule.

    pinned_version_number = NULL  →  use the latest version created by this user;
                                     if no user-owned versions exist → use globally latest.
    pinned_version_number = N     →  always use version N when running pipeline/playground.

    One row per (user, rule) pair — UPSERT on activation.
    """

    __tablename__ = "user_rule_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "rule_id", name="uq_user_rule_preference"),
        {"schema": "profile"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4, comment="Internal UUID"
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profile.user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who owns this preference",
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profile.rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Rule this preference applies to",
    )
    pinned_version_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Pinned version number; NULL = use latest (own first, then global)",
    )

    # Relationships
    rule: Mapped["Rule"] = relationship(back_populates="user_preferences", lazy="selectin")


class PipelineConfig(Base):
    """Pipeline configuration snapshots (config.yaml): batch_size, llm settings, etc."""

    __tablename__ = "pipeline_configs"
    __table_args__ = {"schema": "profile"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4, comment="Unique config identifier"
    )
    version_number: Mapped[int] = mapped_column(
        Integer, unique=True, nullable=False, index=True, comment="Version number"
    )
    config_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="Full config.yaml snapshot"
    )
    change_description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Description of changes"
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.user.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who created this version",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True, comment="Is this version active"
    )
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}", comment="Additional metadata"
    )
