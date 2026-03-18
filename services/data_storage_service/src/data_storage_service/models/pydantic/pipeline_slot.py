"""
Pydantic models for pipeline queue management
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from service.models.enums import PipelineSlotStatus


class PipelineSlotBase(BaseModel):
    """Base pipeline queue schema"""

    position: int = Field(..., description="Position in queue")
    priority: int = Field(0, description="Priority (higher = process first)")


class PipelineSlotCreate(PipelineSlotBase):
    """Create new pipeline queue entry"""

    user_id: UUID | None = None
    guest_session_id: UUID | None = None
    task_id: UUID


class PipelineSlotUpdate(BaseModel):
    """Update existing pipeline queue entry"""

    position: int | None = None
    status: PipelineSlotStatus | None = None
    priority: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class PipelineSlotResponse(PipelineSlotBase):
    """Pipeline queue response"""

    id: UUID
    user_id: UUID | None
    guest_session_id: UUID | None
    task_id: UUID
    status: PipelineSlotStatus
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SlotStatistics(BaseModel):
    """Queue statistics aggregation"""

    queued: int = Field(0, description="Number of queued entries")
    running: int = Field(0, description="Number of running entries")
    completed: int = Field(0, description="Number of completed entries")
    failed: int = Field(0, description="Number of failed entries")
    cancelled: int = Field(0, description="Number of cancelled entries")
