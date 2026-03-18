"""
Background task models for Celery
Technical tasks different from business-level communication_task
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from service.models.db.base_db_model import Base

if TYPE_CHECKING:
    # Type checking only - avoid runtime import of deprecated models
    pass


class Task(Base):
    """Technical Celery tasks (async operations)
    
    Unified task model for all background operations.
    Replaces CommunicationTask for new tasks while maintaining backward compatibility.
    """

    __tablename__ = "tasks"
    __table_args__ = {"schema": "profile"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4, comment="Unique task identifier"
    )
    
    # DEPRECATED: For backward compatibility only. Use user_id directly.
    communication_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.communication_task.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="[DEPRECATED] Related business communication task",
    )
    
    # Ownership
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.user.id", ondelete="SET NULL"),
        nullable=True, 
        index=True,
        comment="Task owner (registered user)",
    )
    guest_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.guest_session.id", ondelete="SET NULL"),
        nullable=True, 
        index=True,
        comment="Task owner (guest session)",
    )
    
    task_type: Mapped[str] = mapped_column(
        String(100),
        comment="Task type: playground_single, playground_batch, pipeline, etc.",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        comment="Status: pending, processing, completed, failed, cancelled, retry",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Execution priority (higher = more important)",
    )

    # Task configuration and data
    payload: Mapped[dict] = mapped_column(
        JSONB, 
        default=dict,
        comment="Task execution data (communications, config, etc.)"
    )
    config: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Task configuration (batch_size, max_parallel_batches, include_risk_ids, etc.)"
    )
    result: Mapped[dict | None] = mapped_column(
        JSONB, 
        nullable=True, 
        comment="Execution result"
    )
    error_message: Mapped[str | None] = mapped_column(
        String, 
        nullable=True, 
        comment="Error message"
    )
    
    # Related file (for tasks with file upload)
    file_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Related file (config, dataset, etc.)",
    )
    
    # Artifacts (for pipeline tasks)
    artifact_paths: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Paths to generated artifacts (reports, plots, etc.)"
    )
    
    # Parent task (for batch sub-tasks)
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profile.tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Parent task (for batch sub-tasks)",
    )
    
    # Celery integration
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True, 
        index=True,
        comment="Celery task ID"
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0, 
        comment="Number of retry attempts"
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3, 
        comment="Maximum retry attempts"
    )
    
    # Timestamps
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True, 
        index=True,
        comment="Scheduled execution time"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True, 
        comment="Execution start time"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True, 
        comment="Execution completion time"
    )


class TaskConcurrency(Base):
    """Tracks currently running task threads for concurrency management
    
    This table helps enforce max_project_threads limit across all task types.
    Entries are created when task starts and removed when task completes.
    """

    __tablename__ = "task_concurrency"
    __table_args__ = {"schema": "profile"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4, comment="Unique concurrency record"
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profile.tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
        comment="Associated task",
    )
    task_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Task type for tracking by type",
    )
    threads_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Number of threads reserved for this task",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="When threads were reserved",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When threads were released (for history)",
    )
