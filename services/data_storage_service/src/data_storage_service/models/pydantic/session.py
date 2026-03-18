"""
Pydantic models for sessions (Pushi)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from service.models.enums import SessionStatus


class UserSessionResponse(BaseModel):
    """Authenticated user session response"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    token: str
    refresh_token: str | None = None
    fingerprint: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    status: SessionStatus
    expires_at: datetime
    created_at: datetime
    updated_at: datetime | None


class UserSessionCreate(BaseModel):
    """Create new user session"""

    user_id: UUID
    token: str
    refresh_token: str | None = None
    fingerprint: str | None = None
    ip_address: str | None = Field(None, max_length=45)
    user_agent: str | None = Field(None, max_length=500)
    expires_at: datetime


class GuestSessionResponse(BaseModel):
    """Guest session response"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_token: str
    fingerprint: str | None = None
    ip_address: str | None = None
    expires_at: datetime
    converted_to_user_id: UUID | None = None
    created_at: datetime


class GuestSessionCreate(BaseModel):
    """Create new guest session"""

    session_token: str
    fingerprint: str | None = None
    ip_address: str | None = Field(None, max_length=45)
    expires_at: datetime
