"""
Auth Schemas — Pydantic-модели для аутентификации и авторизации.

Содержит:
  UserRole      — enum ролей (используется во всём сервисе)
  TokenPayload  — внутреннее представление JWT payload
  LoginRequest  — тело POST /auth/login
  RegisterRequest — тело POST /auth/register
  TokenResponse — ответ на login/refresh
  RefreshRequest — тело POST /auth/refresh
  UserContext   — контекст авторизованного пользователя (dependency)
  UserUpdate    — тело PUT /auth/me
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ─── UserRole ────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    """Роли пользователей в системе (по возрастанию прав)."""

    VIEWER = "viewer"         # только просмотр
    OPERATOR = "operator"     # управление роботами
    SUPERVISOR = "supervisor" # управление + задачи
    ADMIN = "admin"           # полный доступ
    ROBOT = "robot"           # служебная роль для роботов


# Иерархия ролей: чем выше индекс, тем больше прав
ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.VIEWER: 0,
    UserRole.ROBOT: 1,
    UserRole.OPERATOR: 2,
    UserRole.SUPERVISOR: 3,
    UserRole.ADMIN: 4,
}


def has_role_or_higher(user_role: UserRole, required_role: UserRole) -> bool:
    """Проверяет, имеет ли роль пользователя достаточный уровень прав."""
    return ROLE_HIERARCHY.get(user_role, -1) >= ROLE_HIERARCHY.get(required_role, 999)


# ─── JWT Payload ──────────────────────────────────────────────────────────────

class TokenPayload(BaseModel):
    """Декодированный payload JWT токена."""

    sub: str              # user_id (UUID)
    role: str             # UserRole value
    exp: int              # Unix timestamp истечения
    iat: int              # Unix timestamp создания
    jti: str              # JWT ID — уникальный идентификатор для blacklist
    token_type: str = "access"   # "access" или "refresh"

    @property
    def user_id(self) -> str:
        return self.sub

    @property
    def user_role(self) -> UserRole:
        return UserRole(self.role)


# ─── Запросы ────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Тело запроса POST /auth/login."""

    username: str = Field(..., min_length=1, max_length=100, description="Имя пользователя или email")
    password: str = Field(..., min_length=1, description="Пароль")

    model_config = {"json_schema_extra": {"example": {"username": "operator1", "password": "secret"}}}


class RegisterRequest(BaseModel):
    """Тело запроса POST /auth/register."""

    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.OPERATOR

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Минимальные требования: цифра, буква."""
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("role")
    @classmethod
    def validate_role_not_robot(cls, v: UserRole) -> UserRole:
        """Нельзя зарегистрировать пользователя с ролью ROBOT через API."""
        if v == UserRole.ROBOT:
            raise ValueError("Cannot register user with ROBOT role via API")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "new_operator",
                "email": "operator@agentsswarm.io",
                "password": "Secure123",
                "role": "operator",
            }
        }
    }


class RefreshRequest(BaseModel):
    """Тело запроса POST /auth/refresh."""

    refresh_token: str = Field(..., min_length=10)


class UserUpdateRequest(BaseModel):
    """Тело запроса PUT /auth/me."""

    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "UserUpdateRequest":
        if not any([self.email, self.password, self.display_name]):
            raise ValueError("At least one field must be provided for update")
        return self


# ─── Ответы ─────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """Ответ на login/refresh — пара токенов."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Время жизни access token в секундах")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 900,
            }
        }
    }


class UserContext(BaseModel):
    """
    Контекст авторизованного пользователя.
    Возвращается dependency get_current_user и используется во всех роутерах.
    """

    user_id: str
    username: str
    email: str
    role: UserRole
    display_name: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_operator_or_higher(self) -> bool:
        return has_role_or_higher(self.role, UserRole.OPERATOR)

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "operator1",
                "email": "operator1@agentsswarm.io",
                "role": "operator",
            }
        }
    }
