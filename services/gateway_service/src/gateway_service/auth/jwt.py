"""
JWT утилиты: создание и верификация Access + Refresh токенов.

Алгоритм: HS256
Payload:
  sub        — user_id (UUID строка)
  role       — UserRole value
  exp        — Unix timestamp истечения
  iat        — Unix timestamp создания
  jti        — UUID v4, уникальный ID токена (для blacklist при logout)
  token_type — "access" | "refresh"
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from gateway_service.auth.exceptions import AuthError, TokenExpiredError
from gateway_service.auth.schemas import TokenPayload, UserRole
from gateway_service.config import Settings

logger = structlog.get_logger(__name__)

# Ключ в payload для разделения access/refresh
_TOKEN_TYPE_FIELD = "token_type"


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _build_payload(
    subject: str,
    role: str,
    token_type: str,
    expire_delta: timedelta,
) -> dict[str, Any]:
    now = _now_utc()
    return {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + expire_delta).timestamp()),
        "jti": str(uuid.uuid4()),
        _TOKEN_TYPE_FIELD: token_type,
    }


# ─── Создание токенов ────────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    role: str | UserRole,
    settings: Settings,
) -> str:
    """
    Создать Access JWT токен.

    Args:
        subject: user_id (UUID)
        role:    UserRole значение
        settings: объект настроек (содержит JWT_SECRET, JWT_ALGORITHM и т.д.)

    Returns:
        Подписанный JWT-токен в виде строки
    """
    payload = _build_payload(
        subject=subject,
        role=str(role.value if isinstance(role, UserRole) else role),
        token_type="access",
        expire_delta=timedelta(minutes=settings.jwt_access_expire_minutes),
    )
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    subject: str,
    role: str | UserRole,
    settings: Settings,
) -> str:
    """
    Создать Refresh JWT токен (долгоживущий).

    Refresh token содержит минимальный payload — только sub, jti, exp, token_type.
    Роль хранится для удобства повторной выдачи access token без обращения к БД.
    """
    payload = _build_payload(
        subject=subject,
        role=str(role.value if isinstance(role, UserRole) else role),
        token_type="refresh",
        expire_delta=timedelta(days=settings.jwt_refresh_expire_days),
    )
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_token_pair(
    subject: str,
    role: str | UserRole,
    settings: Settings,
) -> tuple[str, str]:
    """Создать пару (access_token, refresh_token) за один вызов."""
    return (
        create_access_token(subject, role, settings),
        create_refresh_token(subject, role, settings),
    )


# ─── Верификация ─────────────────────────────────────────────────────────────

def verify_token(token: str, settings: Settings) -> TokenPayload:
    """
    Декодировать и верифицировать JWT токен.

    Raises:
        TokenExpiredError: если токен истёк
        AuthError:         если токен недействителен (подпись, формат)
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": True},
        )
        return TokenPayload(**payload)

    except ExpiredSignatureError:
        logger.debug("jwt.expired", token_prefix=token[:20])
        raise TokenExpiredError()

    except JWTError as exc:
        logger.warning("jwt.invalid", error=str(exc))
        raise AuthError(f"Invalid token: {exc}") from exc

    except Exception as exc:
        logger.error("jwt.decode_error", error=str(exc))
        raise AuthError("Token validation failed") from exc


def decode_token_unsafe(token: str, settings: Settings) -> TokenPayload | None:
    """
    Декодировать токен БЕЗ проверки exp (для refresh rotation).
    Используется только при обновлении токена — сначала проверяем подпись,
    затем сами проверяем blacklist вместо jose.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},
        )
        return TokenPayload(**payload)
    except Exception:
        return None
