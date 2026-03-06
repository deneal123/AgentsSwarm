"""
Unit-тесты: JWT (auth/jwt.py).

Покрывает:
  - create_access_token / create_refresh_token
  - verify_token: success, expired, invalid signature, wrong type
  - create_token_pair
  - decode_token_unsafe
  - TokenPayload properties: user_id, user_role
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from jose import jwt

from gateway_service.auth.exceptions import AuthError, TokenExpiredError
from gateway_service.auth.jwt import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token_unsafe,
    verify_token,
)
from gateway_service.auth.schemas import UserRole
from gateway_service.config import Settings


# ─── Helpers ─────────────────────────────────────────────────────────────────


USER_ID = "550e8400-e29b-41d4-a716-446655440000"


# ─── create_access_token ─────────────────────────────────────────────────────


def test_create_access_token_returns_string(test_settings: Settings) -> None:
    token = create_access_token(USER_ID, UserRole.OPERATOR, test_settings)
    assert isinstance(token, str)
    assert len(token) > 20


def test_create_access_token_payload(test_settings: Settings) -> None:
    token = create_access_token(USER_ID, UserRole.ADMIN, test_settings)
    payload = jwt.decode(token, test_settings.jwt_secret, algorithms=[test_settings.jwt_algorithm])

    assert payload["sub"] == USER_ID
    assert payload["role"] == "admin"
    assert payload["token_type"] == "access"
    assert "jti" in payload
    assert "exp" in payload
    assert "iat" in payload


def test_create_access_token_expiry(test_settings: Settings) -> None:
    token = create_access_token(USER_ID, UserRole.VIEWER, test_settings)
    payload = jwt.decode(token, test_settings.jwt_secret, algorithms=[test_settings.jwt_algorithm])

    now = int(datetime.now(UTC).timestamp())
    expected_exp = now + test_settings.jwt_access_expire_minutes * 60
    # Допуск 5 секунд
    assert abs(payload["exp"] - expected_exp) < 5


def test_create_access_token_role_as_string(test_settings: Settings) -> None:
    """Принимает как UserRole, так и строку."""
    token = create_access_token(USER_ID, "operator", test_settings)
    payload = jwt.decode(token, test_settings.jwt_secret, algorithms=[test_settings.jwt_algorithm])
    assert payload["role"] == "operator"


# ─── create_refresh_token ────────────────────────────────────────────────────


def test_create_refresh_token_type(test_settings: Settings) -> None:
    token = create_refresh_token(USER_ID, UserRole.OPERATOR, test_settings)
    payload = jwt.decode(token, test_settings.jwt_secret, algorithms=[test_settings.jwt_algorithm])
    assert payload["token_type"] == "refresh"


def test_refresh_token_longer_expiry(test_settings: Settings) -> None:
    access = create_access_token(USER_ID, UserRole.OPERATOR, test_settings)
    refresh = create_refresh_token(USER_ID, UserRole.OPERATOR, test_settings)

    access_payload = jwt.decode(access, test_settings.jwt_secret, algorithms=[test_settings.jwt_algorithm])
    refresh_payload = jwt.decode(refresh, test_settings.jwt_secret, algorithms=[test_settings.jwt_algorithm])

    assert refresh_payload["exp"] > access_payload["exp"]


# ─── create_token_pair ───────────────────────────────────────────────────────


def test_create_token_pair_returns_tuple(test_settings: Settings) -> None:
    access, refresh = create_token_pair(USER_ID, UserRole.OPERATOR, test_settings)
    assert isinstance(access, str)
    assert isinstance(refresh, str)
    # Токены должны быть разными
    assert access != refresh


# ─── verify_token ────────────────────────────────────────────────────────────


def test_verify_token_success(test_settings: Settings) -> None:
    token = create_access_token(USER_ID, UserRole.OPERATOR, test_settings)
    payload = verify_token(token, test_settings)

    assert payload.sub == USER_ID
    assert payload.role == "operator"
    assert payload.token_type == "access"


def test_verify_token_expired(test_settings: Settings) -> None:
    """Истёкший токен → TokenExpiredError."""
    # Создаём токен с exp в прошлом через прямое кодирование
    now = int(datetime.now(UTC).timestamp())
    raw_payload = {
        "sub": USER_ID,
        "role": "operator",
        "iat": now - 120,
        "exp": now - 60,   # уже истёк
        "jti": "test-jti",
        "token_type": "access",
    }
    expired_token = jwt.encode(raw_payload, test_settings.jwt_secret, algorithm=test_settings.jwt_algorithm)

    with pytest.raises(TokenExpiredError):
        verify_token(expired_token, test_settings)


def test_verify_token_invalid_signature(test_settings: Settings) -> None:
    """Неверная подпись → AuthError."""
    token = create_access_token(USER_ID, UserRole.OPERATOR, test_settings)
    # Модифицируем последний байт подписи
    parts = token.split(".")
    parts[2] = parts[2][:-2] + "ZZ"
    bad_token = ".".join(parts)

    with pytest.raises(AuthError):
        verify_token(bad_token, test_settings)


def test_verify_token_garbage_input(test_settings: Settings) -> None:
    with pytest.raises(AuthError):
        verify_token("not.a.jwt", test_settings)


def test_verify_token_empty_string(test_settings: Settings) -> None:
    with pytest.raises(AuthError):
        verify_token("", test_settings)


# ─── decode_token_unsafe ─────────────────────────────────────────────────────


def test_decode_token_unsafe_expired_ok(test_settings: Settings) -> None:
    """decode_token_unsafe не проверяет exp — истёкший токен декодируется."""
    now = int(datetime.now(UTC).timestamp())
    raw_payload = {
        "sub": USER_ID,
        "role": "operator",
        "iat": now - 120,
        "exp": now - 60,
        "jti": "test-jti",
        "token_type": "refresh",
    }
    expired_token = jwt.encode(raw_payload, test_settings.jwt_secret, algorithm=test_settings.jwt_algorithm)

    result = decode_token_unsafe(expired_token, test_settings)
    assert result is not None
    assert result.sub == USER_ID


def test_decode_token_unsafe_garbage(test_settings: Settings) -> None:
    result = decode_token_unsafe("garbage", test_settings)
    assert result is None


# ─── TokenPayload properties ─────────────────────────────────────────────────


def test_token_payload_user_id_property(test_settings: Settings) -> None:
    token = create_access_token(USER_ID, UserRole.ADMIN, test_settings)
    payload = verify_token(token, test_settings)
    assert payload.user_id == USER_ID


def test_token_payload_user_role_property(test_settings: Settings) -> None:
    token = create_access_token(USER_ID, UserRole.SUPERVISOR, test_settings)
    payload = verify_token(token, test_settings)
    assert payload.user_role == UserRole.SUPERVISOR


def test_token_payload_jti_unique(test_settings: Settings) -> None:
    """Каждый токен имеет уникальный jti."""
    t1 = create_access_token(USER_ID, UserRole.OPERATOR, test_settings)
    t2 = create_access_token(USER_ID, UserRole.OPERATOR, test_settings)
    p1 = verify_token(t1, test_settings)
    p2 = verify_token(t2, test_settings)
    assert p1.jti != p2.jti
