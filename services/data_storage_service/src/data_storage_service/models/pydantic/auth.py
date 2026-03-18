"""
Pydantic models for authentication (Pushi)
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from service.models.enums import UserType
from service.models.pydantic.profile import UserResponse


class AuthProfile(BaseModel):
    """Authentication profile for session context"""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID = Field(description="User ID")
    fingerprint: str | None = Field(None, description="Device fingerprint")
    type: UserType = Field(description="User type: guest or registered_user")


class LoginRequest(BaseModel):
    """Login request schema"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "lawyer@example.com",
                "password": "SecurePass123!",
                "fingerprint": "device-fingerprint-hash",
            }
        }
    )

    email: str = Field(min_length=3, max_length=500, description="Email address")
    password: str = Field(min_length=8, max_length=255, description="Password")
    fingerprint: str | None = Field(None, description="Device fingerprint")


class LoginResponse(BaseModel):
    """Login response with tokens and user info"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "lawyer@example.com",
                    "first_name": "Анна",
                    "last_name": "Иванова",
                    "is_active": True,
                    "timezone": "Europe/Moscow",
                    "created_at": "2026-01-09T12:00:00Z",
                },
            }
        }
    )

    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="JWT refresh token")
    user: "UserResponse" = Field(description="User profile information")


class TokenRefreshRequest(BaseModel):
    """Token refresh request"""

    model_config = ConfigDict(
        json_schema_extra={"example": {"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}}
    )

    refresh_token: str = Field(description="Valid refresh token")


class TokenRefreshResponse(BaseModel):
    """Token refresh response with new tokens"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
    )

    access_token: str = Field(description="New JWT access token")
    refresh_token: str = Field(description="New JWT refresh token")


class RegisterResponse(BaseModel):
    """Registration response with user and tokens"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "lawyer@example.com",
                    "first_name": "Анна",
                    "last_name": "Иванова",
                },
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
    )

    user: UserResponse = Field(description="Created user profile")
    access_token: str = Field(description="Initial JWT access token")
    refresh_token: str = Field(description="Initial JWT refresh token")
