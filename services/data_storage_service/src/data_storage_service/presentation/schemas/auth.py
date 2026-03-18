"""Схемы запросов и ответов для эндпоинтов аутентификации и профиля."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ---------------------------------------------------------------------------
# Re-export response types from domain models (source of truth)
# ---------------------------------------------------------------------------
from service.models.pydantic.profile import UserResponse as UserResponse  # noqa: F401
from service.models.pydantic.auth import (
    LoginResponse as LoginResponse,  # noqa: F401
    TokenRefreshResponse as TokenRefreshResponse,  # noqa: F401
)

# ---------------------------------------------------------------------------
# Request schemas (defined here — not in domain models)
# ---------------------------------------------------------------------------


class UserRegisterRequest(BaseModel):
    """Регистрация нового пользователя."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
                "first_name": "Анна",
                "last_name": "Иванова",
                "timezone": "Europe/Moscow",
            }
        }
    )

    email: EmailStr = Field(..., description="Email-адрес")
    password: str = Field(..., min_length=8, max_length=255, description="Пароль (мин. 8 символов)")
    first_name: str | None = Field(None, max_length=100, description="Имя")
    last_name: str | None = Field(None, max_length=100, description="Фамилия")
    timezone: str = Field("UTC", max_length=50, description="Часовой пояс, например Europe/Moscow")


class UserLoginRequest(BaseModel):
    """Вход по email и паролю."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
                "fingerprint": "device-fingerprint-hash",
            }
        }
    )

    email: EmailStr = Field(..., description="Email-адрес")
    password: str = Field(..., description="Пароль")
    fingerprint: str | None = Field(None, description="Отпечаток устройства")


class TokenRefreshRequest(BaseModel):
    """Обновление access-токена."""

    refresh_token: str = Field(..., description="Действующий refresh-токен")


class UserUpdateRequest(BaseModel):
    """Обновление данных профиля."""

    first_name: str | None = Field(None, max_length=100, description="Имя")
    last_name: str | None = Field(None, max_length=100, description="Фамилия")
    timezone: str | None = Field(None, max_length=50, description="Часовой пояс")


# ---------------------------------------------------------------------------
# Response schemas that are not part of domain models
# ---------------------------------------------------------------------------


class GuestTokenResponse(BaseModel):
    """Ответ с токеном гостевой сессии."""

    guest_token: str = Field(..., description="Токен гостевой сессии (использовать как cookie auth_token)")
    guest_session_id: UUID = Field(..., description="UUID гостевой сессии")
    expires_at: datetime = Field(..., description="Время истечения сессии (UTC)")


class LogoutResponse(BaseModel):
    """Ответ на выход из системы."""

    message: str = "Вы успешно вышли из системы"


# Session Schemas

class SessionResponse(BaseModel):
    """Response with session details."""
    
    id: UUID
    user_id: UUID
    status: str
    expires_at: datetime
    created_at: datetime
    user_agent: Optional[str]
