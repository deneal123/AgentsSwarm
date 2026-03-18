"""
Models for communication classification results.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from service.models.db.base_db_model import Base

if TYPE_CHECKING:
    from service.models.db.risk_models import Rule
    from service.models.db.user_models import User
    from service.models.db.session_models import GuestSession


class CommunicationTask(Base):
    """Business entity: batch of communications for risk analysis."""

    __tablename__ = "communication_task"
    __table_args__ = {"schema": "profile"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4
    )
    batch_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.user.id", ondelete="CASCADE"), nullable=True
    )
    guest_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.guest_session.id", ondelete="CASCADE"), nullable=True
    )
    pipeline_config_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.pipeline_configs.id", ondelete="SET NULL"), nullable=True
    )
    product_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    total_communications: Mapped[int | None] = mapped_column(Integer)
    processed_communications: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    error_text: Mapped[str | None] = mapped_column(Text)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="communication_tasks")
    communications: Mapped[list["Communication"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class Communication(Base):
    """Individual push/SMS messages."""

    __tablename__ = "communication"
    __table_args__ = {"schema": "profile"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4
    )
    communication_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profile.communication_task.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    ai: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    product_type: Mapped[str] = mapped_column(String(100), nullable=False)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    task: Mapped["CommunicationTask"] = relationship(back_populates="communications")
    results: Mapped[list["CommunicationResult"]] = relationship(
        back_populates="communication", cascade="all, delete-orphan"
    )


class CommunicationResult(Base):
    """Classification results for a communication."""

    __tablename__ = "communication_result"
    __table_args__ = {"schema": "profile"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4
    )
    communication_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profile.communication.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profile.communication_task.id", ondelete="CASCADE"), nullable=False
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.rules.id", ondelete="SET NULL")
    )
    risk_ids_pred: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    risk_info: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    triggers: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict)
    reasoning: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    processing_time_ms: Mapped[int | None] = mapped_column(Integer)
    model_used: Mapped[str | None] = mapped_column(String(100))
    error_text: Mapped[str | None] = mapped_column(Text)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    communication: Mapped["Communication"] = relationship(back_populates="results")
    rule: Mapped["Rule"] = relationship(back_populates="communication_results")
