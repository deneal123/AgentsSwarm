"""
Session models for authenticated and guest users
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from service.models.db.base_db_model import Base

if TYPE_CHECKING:
    from service.models.db.user_models import User


class UserSession(Base):
    """Authenticated user sessions"""

    __tablename__ = "user_session"
    __table_args__ = {"schema": "session"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4, comment="Unique session identifier"
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profile.user.id", ondelete="CASCADE"),
        index=True,
        comment="Reference to user",
    )
    fingerprint: Mapped[str | None] = mapped_column(String(255), comment="Browser fingerprint hash")
    user_agent: Mapped[str | None] = mapped_column(String(500), comment="Browser user agent string")
    ip_address: Mapped[str | None] = mapped_column(String(45), comment="IP address for logging")
    status: Mapped[str] = mapped_column(
        String(50), default="active", comment="Session status: active, expired, revoked"
    )
    token: Mapped[str] = mapped_column(String, unique=True, comment="JWT token")
    refresh_token: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True, comment="Refresh token"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), comment="Session expiration timestamp"
    )

    user: Mapped["User"] = relationship(back_populates="user_sessions", lazy="selectin")


class GuestSession(Base):
    """Guest sessions for anonymous users"""

    __tablename__ = "guest_session"
    __table_args__ = {"schema": "profile"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4, comment="Unique session identifier"
    )
    session_token: Mapped[str] = mapped_column(
        String, unique=True, comment="Unique token for guest identification"
    )
    fingerprint: Mapped[str | None] = mapped_column(String(255), comment="Browser fingerprint")
    ip_address: Mapped[str | None] = mapped_column(
        String(45), comment="IP address for rate limiting"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), comment="Session expiration time"
    )
    converted_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.user.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID after registration",
    )
