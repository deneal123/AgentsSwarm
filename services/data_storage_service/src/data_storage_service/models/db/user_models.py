"""
User and authentication models for Pushi
Simplified for legal professionals using risk analysis platform
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from service.models.db.base_db_model import Base
from service.models.enums import UserLaunchStatus, UserLaunchType
from sqlalchemy import ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from service.models.db.communication_models import CommunicationTask
    from service.models.db.file_models import File
    from service.models.db.session_models import UserSession


class User(Base):
    """Legal professionals (lawyers, compliance specialists)"""

    __tablename__ = "user"
    __table_args__ = {"schema": "profile"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4, comment="Unique user identifier"
    )
    email: Mapped[str] = mapped_column(
        String(500), unique=True, nullable=False, comment="User email address"
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="Hashed password")
    first_name: Mapped[str | None] = mapped_column(String(100), comment="User first name")
    last_name: Mapped[str | None] = mapped_column(String(100), comment="User last name")
    is_active: Mapped[bool] = mapped_column(default=True, comment="Is account active")
    timezone: Mapped[str] = mapped_column(
        String(50), default="UTC", comment="Preferred timezone"
    )
    role: Mapped[str] = mapped_column(
        String(50),
        server_default=text("'lawyer'"),
        default="lawyer",
        comment="User role: lawyer | admin",
    )

    # Relationships
    user_launches: Mapped[list["UserLaunch"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="user",
        lazy="selectin",
    )
    user_sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    communication_tasks: Mapped[list["CommunicationTask"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class UserLaunch(Base):
    """User activity tracking (communication analysis, rule updates, etc.)"""

    __tablename__ = "user_launch"
    __table_args__ = {"schema": "profile"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4, comment="Unique launch identifier"
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.user.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
        comment="Reference to user (null for guest sessions)",
    )
    guest_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.guest_session.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
        comment="Reference to guest session",
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.communication_task.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
        comment="Related communication task",
    )
    launch_type: Mapped[UserLaunchType] = mapped_column(
        String(50), comment="Launch type: communication_analysis, rule_update, etc."
    )
    status: Mapped[UserLaunchStatus] = mapped_column(
        String(50), default="initiated", comment="Launch status"
    )
    payload: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Launch parameters and metadata"
    )

    # Relationships
    user: Mapped["User"] = relationship(
        back_populates="user_launches",
        lazy="selectin",
    )
    task: Mapped["CommunicationTask"] = relationship(
        foreign_keys=[task_id],
        lazy="selectin",
    )
