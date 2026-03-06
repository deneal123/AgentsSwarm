"""
FastAPI dependencies для аутентификации.

get_current_user          — обязательная авторизация (401 если нет/невалидный токен)
get_current_user_optional — опциональная (None если нет токена)

Особенности:
  - Извлекает токен из Authorization: Bearer <token> ИЛИ query-параметра ?token=
    (второй нужен для WebSocket-подключений, браузер не может задать заголовки для WS)
  - Проверяет blacklist в Redis (ключ jwt:blacklist:{jti})
  - Привязывает user context к structlog contextvars для логирования
"""

from __future__ import annotations

import structlog
from fastapi import Depends, Query, Request
from fastapi.security import OAuth2PasswordBearer

from gateway_service.auth.exceptions import AuthError, TokenBlacklistedError, TokenExpiredError
from gateway_service.auth.jwt import verify_token
from gateway_service.auth.schemas import UserContext
from gateway_service.config import Settings, get_settings

logger = structlog.get_logger(__name__)

# Стандартная схема — ищет токен в Authorization: Bearer
_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,  # не бросаем 401 сами — делаем это ниже с нужным телом ответа
)

# Redis ключ для blacklist
_BLACKLIST_PREFIX = "jwt:blacklist:"


def _make_blacklist_key(jti: str) -> str:
    return f"{_BLACKLIST_PREFIX}{jti}"


async def _extract_token(
    request: Request,
    bearer_token: str | None,
    token_query: str | None,
) -> str | None:
    """Извлечь JWT из Bearer header или query-параметра."""
    if bearer_token:
        return bearer_token
    if token_query:
        return token_query
    # Попытка прочитать вручную из заголовка (на случай нестандартных клиентов)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip()
    return None


async def _check_blacklist(redis: object | None, jti: str) -> bool:
    """Проверить, отозван ли токен (True = в blacklist)."""
    if redis is None:
        return False
    try:
        value = await redis.get(_make_blacklist_key(jti))  # type: ignore[union-attr]
        return value is not None
    except Exception as exc:
        logger.warning("jwt.blacklist_check_failed", jti=jti, error=str(exc))
        return False  # fail-open: если Redis недоступен — не блокируем


async def get_current_user(
    request: Request,
    bearer_token: str | None = Depends(_oauth2_scheme),
    token_query: str | None = Query(default=None, alias="token", include_in_schema=False),
    settings: Settings = Depends(get_settings),
) -> UserContext:
    """
    FastAPI Dependency: извлечь и верифицировать JWT, вернуть UserContext.

    Raises:
        AuthError:           если токен отсутствует или невалидный
        TokenExpiredError:   если токен истёк
        TokenBlacklistedError: если токен в blacklist
    """
    from fastapi import HTTPException, status

    token = await _extract_token(request, bearer_token, token_query)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "MISSING_TOKEN", "message": "Authentication required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_token(token, settings)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "TOKEN_EXPIRED", "message": "Token has expired"},
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_TOKEN", "message": exc.message},
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )

    # Только access-токены допускаются для обычных запросов
    if payload.token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "WRONG_TOKEN_TYPE", "message": "Access token required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Проверка blacklist
    redis = getattr(request.app.state, "redis", None)
    if await _check_blacklist(redis, payload.jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "TOKEN_REVOKED", "message": "Token has been revoked"},
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )

    # Привязываем к structlog context (будет в каждом лог-сообщении этого запроса)
    structlog.contextvars.bind_contextvars(user_id=payload.sub, role=payload.role)

    # Также сохраняем в request.state для доступа из HTTP middleware
    # (BaseHTTPMiddleware не имеет доступа к structlog contextvars из вложенных задач)
    request.state.user_id = payload.sub

    return UserContext(
        user_id=payload.sub,
        username="",    # будет заполнено из user_service при необходимости
        email="",
        role=payload.user_role,
    )


async def get_current_user_optional(
    request: Request,
    bearer_token: str | None = Depends(_oauth2_scheme),
    token_query: str | None = Query(default=None, alias="token", include_in_schema=False),
    settings: Settings = Depends(get_settings),
) -> UserContext | None:
    """
    Опциональная dependency — возвращает None если токен не предоставлен.
    Исключение бросается только если токен есть, но он невалиден.
    """
    token = await _extract_token(request, bearer_token, token_query)
    if not token:
        return None

    # Если токен есть — проверяем его строго
    return await get_current_user(request, bearer_token, token_query, settings)


async def add_token_to_blacklist(
    request: Request,
    jti: str,
    ttl_seconds: int,
) -> None:
    """
    Добавить JTI в Redis blacklist с TTL = оставшееся время жизни токена.
    Вызывается при logout.
    """
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        logger.warning("jwt.blacklist_skip", reason="Redis not available")
        return
    try:
        await redis.set(_make_blacklist_key(jti), "1", ttl=ttl_seconds)
        logger.info("jwt.blacklisted", jti=jti, ttl=ttl_seconds)
    except Exception as exc:
        logger.error("jwt.blacklist_failed", jti=jti, error=str(exc))
