from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class GetProfileOverviewQuery(BaseModel):
    user_id: UUID


class UpdateProfileCommand(BaseModel):
    user_id: UUID
    first_name: str | None = None
    timezone: str | None = None
    avatar_url: str | None = None


class DeleteChatHistoryCommand(BaseModel):
    user_id: UUID


class ProfileOverviewResult(BaseModel):
    id: UUID
    email: str
    first_name: str | None
    timezone: str | None
    avatar_url: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EmailField(BaseModel):
    email: Annotated[EmailStr, Field(..., description="User email", min_length=5, max_length=500)]


class RegisterRequest(EmailField):
    password: Annotated[
        str,
        Field(..., min_length=8, max_length=100, description="User password"),
    ]
    fingerprint: Annotated[
        str | None,
        Field(None, min_length=10, max_length=1000, description="User device fingerprint"),
    ]


class RegisterResponse(EmailField):
    user_id: Annotated[UUID, Field(..., description="User ID")]


class LoginRequest(EmailField):
    password: Annotated[str, Field(..., description="User password", min_length=4, max_length=100)]


class LoginResponse(BaseModel):
    jwt: Annotated[str, Field(..., description="JWT token with user profile")]
