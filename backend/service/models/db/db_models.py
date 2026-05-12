from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from service.models.db.base_db_model import Base
from service.models.key_value import (
    ProcessingStatus,
    ServiceType,
    SessionStatus,
)


class User(Base):
    __tablename__ = "user"
    __table_args__ = {"schema": "profile"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4, comment="Unique user identifier"
    )
    email: Mapped[str] = mapped_column(String(500), unique=True, comment="User email address")
    password_hash: Mapped[str] = mapped_column(String(255), comment="Hashed user password")
    available_launches: Mapped[int] = mapped_column(Integer, nullable=False, comment="Number of available launches")
    first_name: Mapped[str | None] = mapped_column(String(50), comment="User first name")
    timezone: Mapped[str | None] = mapped_column(String(50), comment="Preferred timezone name")
    avatar_url: Mapped[str | None] = mapped_column(String(1000), comment="Public avatar URL")

    user_launches: Mapped[list["UserLaunch"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="user",
        lazy="selectin",
    )

    # Files owned by the user
    user_files: Mapped[list["UserFile"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="user",
        lazy="selectin",
    )


class UserLaunch(Base):
    __tablename__ = "user_launch"
    __table_args__ = {"schema": "profile"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4, comment="Unique launch identifier"
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profile.user.id", ondelete="CASCADE"),
        index=True,
        comment="Reference to user",
    )
    type: Mapped[ServiceType] = mapped_column(Enum(ServiceType, name="service_type", create_type=True), comment="Launch type")
    status: Mapped[ProcessingStatus] = mapped_column(String(50), comment="Launch status")
    payload: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Optional JSON payload with job parameters"
    )

    # Celery task tracking
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Celery task ID for job tracking"
    )
    celery_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Celery task status"
    )

    user: Mapped["User"] = relationship(
        back_populates="user_launches",
        lazy="selectin",
    )


class UserSession(Base):
    __tablename__ = "user_session"
    __table_args__ = {"schema": "session"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4, comment="Unique session identifier"
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, index=True, comment="Reference to user")
    fingerprint: Mapped[str | None] = mapped_column(String(50), comment="Browser fingerprint hash")
    user_agent: Mapped[str | None] = mapped_column(String(255), comment="Browser user agent string")
    status: Mapped[SessionStatus] = mapped_column(String, comment="Session status")
    token: Mapped[str | None] = mapped_column(String, comment="Session authentication token")
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), comment="Session expiration timestamp"
    )
    session_code: Mapped[str] = mapped_column(String, comment="Session verification code")


class UserFile(Base):
    __tablename__ = "user_file"
    __table_args__ = {"schema": "profile"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4, comment="Unique image identifier"
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profile.user.id", ondelete="CASCADE"),
        index=True,
        comment="Reference to user",
    )
    type: Mapped[ServiceType] = mapped_column(Enum(ServiceType, name="service_type", create_type=False), name="mode", comment="service type")
    file_name: Mapped[str] = mapped_column(String(1000), comment="file name")
    file_url: Mapped[str] = mapped_column(String(1000), comment="file path or URL")

    user: Mapped["User"] = relationship(
        back_populates="user_files",
        lazy="selectin",
    )


