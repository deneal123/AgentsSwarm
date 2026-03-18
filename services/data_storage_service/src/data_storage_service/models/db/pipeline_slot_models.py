"""
Pipeline slot models.
Ensures sequential processing (prevents parallel pipeline runs per user).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from service.models.db.base_db_model import Base
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

if TYPE_CHECKING:
    from service.models.db.communication_models import CommunicationTask
    from service.models.db.session_models import GuestSession
    from service.models.db.user_models import User


class PipelineSlot(Base):
    """Sequential processing slot (prevents parallel pipeline runs per user)."""

    __tablename__ = "pipeline_queue"
    __table_args__ = {"schema": "profile"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4, comment="Unique slot entry identifier"
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.user.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="User who queued the task",
    )
    guest_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.guest_session.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Guest session who queued the task",
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profile.communication_task.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="Reference to communication task",
    )
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment="Position in slot queue"
    )
    status: Mapped[str] = mapped_column(
        String(50), default="queued", nullable=False, index=True, comment="Slot status"
    )
    priority: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="Priority (higher = process first)"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Processing start time"
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Processing finish time"
    )
