"""Pydantic models for Communication and CommunicationResult."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Communication Result
# ============================================================================


class CommunicationResultResponse(BaseModel):
    """Classification result for a single communication."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    communication_id: UUID
    task_id: UUID
    rule_id: UUID | None = None
    risk_ids_pred: list[str] = Field(default_factory=list)
    risk_info: dict[str, Any] = Field(default_factory=dict)
    triggers: dict[str, Any] | None = None
    reasoning: str | None = None
    status: str
    processing_time_ms: int | None = None
    model_used: str | None = None
    error_text: str | None = None
    extra_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    finished_at: datetime | None = None


class CommunicationResultSummary(BaseModel):
    """Compact view for listing — without heavy risk_info / triggers."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    communication_id: UUID
    task_id: UUID
    rule_id: UUID | None = None
    risk_ids_pred: list[str] = Field(default_factory=list)
    status: str
    processing_time_ms: int | None = None
    model_used: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


# ============================================================================
# Communication (the input message)
# ============================================================================


class CommunicationResponse(BaseModel):
    """Individual communication with its classification results."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    communication_id: str
    task_id: UUID
    text: str
    ai: int
    type: str
    product_type: str
    extra_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    processed_at: datetime | None = None
    # Inline results (populated separately)
    results: list[CommunicationResultResponse] = Field(default_factory=list)


class CommunicationSummary(BaseModel):
    """Compact communication row for search/filter tables."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    communication_id: str
    task_id: UUID
    text: str
    type: str
    product_type: str
    created_at: datetime
    processed_at: datetime | None = None
    # Aggregate stats
    risk_ids_pred: list[str] = Field(
        default_factory=list,
        description="Union of all predicted risk IDs across all results",
    )
    result_count: int = 0
    has_risks: bool = False


# ============================================================================
# Paginated list response
# ============================================================================


class CommunicationResultPage(BaseModel):
    """Paginated list of communication results for a task."""

    task_id: UUID
    items: list[CommunicationSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# ============================================================================
# Task-level statistics
# ============================================================================


class TaskCommunicationStats(BaseModel):
    """Aggregated statistics for communications of a single task run."""

    task_id: UUID
    total_communications: int = 0
    processed: int = 0
    with_risks: int = 0
    without_risks: int = 0
    failed: int = 0
    unique_risk_ids: list[str] = Field(default_factory=list)
    risk_counts: dict[str, int] = Field(
        default_factory=dict,
        description="How many communications triggered each risk_id",
    )
    avg_processing_time_ms: float | None = None
    models_used: list[str] = Field(default_factory=list)


# ============================================================================
# Bulk create input (used by tasks internally)
# ============================================================================


class CommunicationResultCreate(BaseModel):
    """Input for bulk-saving analysis results from a worker."""

    task_id: UUID
    communication_text: str
    communication_type: str = "push"
    product_type: str = "all"
    extra_metadata: dict[str, Any] = Field(default_factory=dict)
    # Result fields
    risk_ids_pred: list[str] = Field(default_factory=list)
    risk_info: dict[str, Any] = Field(default_factory=dict)
    triggers: dict[str, Any] | None = None
    reasoning: str | None = None
    status: str = "completed"
    processing_time_ms: int | None = None
    model_used: str | None = None
    error_text: str | None = None
    rule_id: UUID | None = None
