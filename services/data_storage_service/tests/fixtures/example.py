"""Shared fixtures and models for chat-related tests."""

import uuid
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseTest(DeclarativeBase):
    """Base declarative model for SQLite-backed tests."""

    pass


class ChatThreadTest(BaseTest):
    """SQLite-compatible ChatThread model for tests."""

    __tablename__ = "chat_threads"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), unique=True, default=uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    guest_session_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )
    thread_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    extra_metadata: Mapped[dict | None] = mapped_column(JSON, default=None, nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, onupdate=datetime.now
    )


class ChatMessageTest(BaseTest):
    """SQLite-compatible ChatMessage model for tests."""

    __tablename__ = "chat_messages"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), unique=True, default=uuid4)
    thread_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_threads.id"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    sender_type: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(String)
    content_tokens: Mapped[int | None] = mapped_column(nullable=True)
    is_edited: Mapped[bool] = mapped_column(default=False)
    extra_metadata: Mapped[dict | None] = mapped_column(JSON, default=None, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, onupdate=datetime.now
    )


class ChatMessageFileTest(BaseTest):
    """SQLite-compatible ChatMessageFile model for tests."""

    __tablename__ = "chat_message_files"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    file_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class FileTest(BaseTest):
    """SQLite-compatible File model for attachment metadata."""

    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    file_name: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column(String(1000), unique=True)
    storage_type: Mapped[str] = mapped_column(String(50), default="local")
    file_size: Mapped[int] = mapped_column()
    mime_type: Mapped[str] = mapped_column(String(100))
    file_type: Mapped[str] = mapped_column(String(50))
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    is_public: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class MessageReadStatusTest(BaseTest):
    """SQLite-compatible MessageReadStatus model for tests."""

    __tablename__ = "message_read_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class ChatTypingIndicatorTest(BaseTest):
    """SQLite-compatible typing indicator model for tests."""

    __tablename__ = "chat_typing_indicators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    guest_session_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )
    is_typing: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class ChatMessageReactionTest(BaseTest):
    """SQLite-compatible reaction model for tests."""

    __tablename__ = "chat_message_reactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reaction_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), unique=True, default=uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    guest_session_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )
    reaction_type: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


@pytest.fixture
def patch_chat_models(monkeypatch):
    """Patch chat repository models to use SQLite test counterparts."""
    import service.repositories.chat_repository as chat_repo
    import service.services.chat_service as chat_service_module

    with patch.multiple(
        chat_repo,
        ChatThread=ChatThreadTest,
        ChatMessage=ChatMessageTest,
        ChatMessageFile=ChatMessageFileTest,
        MessageReadStatus=MessageReadStatusTest,
        ChatTypingIndicator=ChatTypingIndicatorTest,
        ChatMessageReaction=ChatMessageReactionTest,
        File=FileTest,
    ):
        with patch.multiple(
            chat_service_module,
            ChatThread=ChatThreadTest,
            ChatMessage=ChatMessageTest,
            ChatTypingIndicator=ChatTypingIndicatorTest,
            ChatMessageReaction=ChatMessageReactionTest,
            File=FileTest,
        ):
            yield
