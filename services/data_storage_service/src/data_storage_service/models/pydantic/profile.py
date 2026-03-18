"""
Pydantic models for user profiles (Pushi)
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    """User profile response for legal professionals"""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "lawyer@example.com",
                "first_name": "Анна",
                "last_name": "Иванова",
                "is_active": True,
                "timezone": "Europe/Moscow",
                "created_at": "2026-01-01T10:00:00Z",
                "updated_at": "2026-01-09T12:00:00Z",
            }
        },
    )

    id: UUID
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool = True
    timezone: str = "UTC"
    created_at: datetime
    updated_at: datetime | None

    # Optional role field — added so AuthService can resolve user role when present
    role: str | None = None


class UserCreate(BaseModel):
    """Create new user account"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "lawyer@example.com",
                "password": "SecurePass123!",
                "first_name": "Анна",
                "last_name": "Иванова",
                "timezone": "Europe/Moscow",
            }
        }
    )

    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    timezone: str = Field("UTC", max_length=50)


class UserUpdate(BaseModel):
    """Update user profile"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "Анна",
                "last_name": "Петрова",
                "timezone": "Europe/Moscow",
            }
        }
    )

    email: EmailStr | None = None
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    timezone: str | None = Field(None, max_length=50)


class UserProfileLogic(BaseModel):
    """User profile logic model (for internal use)"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    first_name: str | None
    last_name: str | None
    is_active: bool
    timezone: str


# ============================================================================
# USER LAUNCH MODELS
# ============================================================================


class UserLaunchBase(BaseModel):
    """Base user launch schema"""

    launch_type: str = Field(..., max_length=50, description="Launch type")
    payload: dict[str, Any] = Field(default_factory=dict, description="Launch parameters")


class UserLaunchCreate(UserLaunchBase):
    """Create new user launch"""

    user_id: UUID | None = None
    guest_session_id: UUID | None = None
    task_id: UUID | None = None


class UserLaunchUpdate(BaseModel):
    """Update user launch"""

    status: str | None = Field(None, max_length=50)
    payload: dict[str, Any] | None = None


class UserLaunchResponse(UserLaunchBase):
    """User launch response"""

    id: UUID
    user_id: UUID | None
    guest_session_id: UUID | None
    task_id: UUID | None
    status: str
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
