"""
File storage models for Pushi
Handles datasets, etalons, results, and documents
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from service.models.db.base_db_model import Base
from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON


class File(Base):
    """Universal file storage for datasets, results, and documents"""

    __tablename__ = "files"
    __table_args__ = {"schema": "profile"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4, comment="Unique file identifier"
    )
    file_name: Mapped[str] = mapped_column(String(255), comment="Original file name")
    file_path: Mapped[str] = mapped_column(
        String(1000), comment="Path in storage (local/S3/MinIO) or URL"
    )
    storage_type: Mapped[str] = mapped_column(
        String(20), default="local", comment="Storage type: local, s3, minio"
    )
    file_size: Mapped[int] = mapped_column(BigInteger, comment="File size in bytes")
    mime_type: Mapped[str] = mapped_column(String(100), comment="MIME type")
    file_type: Mapped[str] = mapped_column(
        String(50),
        comment="File category: communication_dataset, etalon_dataset, result_xlsx, etc.",
    )
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.user.id", ondelete="SET NULL"),
        nullable=True,
        comment="Uploader user ID",
    )
    uploaded_by_guest_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.guest_session.id", ondelete="SET NULL"),
        nullable=True,
        comment="Uploader guest session ID",
    )
    is_public: Mapped[bool] = mapped_column(default=False, comment="Public access flag")
    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Additional file metadata (scan results, image info, etc.)"
    )

    @property
    def storage_path(self) -> str:
        return self.file_path

    @property
    def uploaded_at(self) -> datetime | None:
        return self.created_at
