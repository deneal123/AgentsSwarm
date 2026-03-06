"""
Auth endpoints:
  POST /api/v1/auth/login    — получить пару токенов
  POST /api/v1/auth/register — регистрация (только ADMIN может задать роль)
  GET  /api/v1/auth/me       — профиль текущего пользователя
  PUT  /api/v1/auth/me       — обновить профиль (email, пароль, display_name)
  POST /api/v1/auth/refresh  — обновить access token по refresh token
  POST /api/v1/auth/logout   — отозвать refresh token (добавить в blacklist)
"""

from __future__ import annotations

import time

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response

from gateway_service.auth.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from gateway_service.auth.jwt import (
    create_token_pair,
    decode_token_unsafe,
    verify_token,
)
from gateway_service.auth.middleware import add_token_to_blacklist, get_current_user
from gateway_service.auth.permissions import require_admin
from gateway_service.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserContext,
    UserRole,
    UserUpdateRequest,
)
from gateway_service.config import Settings, get_settings
from gateway_service.services.user_service import AbstractUserService, get_user_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _build_token_response(
    user_id: str,
    role: UserRole | str,
    settings: Settings,
) -> TokenResponse:
    access_token, refresh_token = create_token_pair(user_id, role, settings)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_expire_minutes * 60,
    )


def _user_record_to_context(user: object) -> UserContext:  # type: ignore[return]
    """Конвертировать UserRecord → UserContext."""
    from gateway_service.services.user_service import UserRecord
    if isinstance(user, UserRecord):
        return UserContext(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            role=UserRole(user.role),
            display_name=user.display_name,
        )
    raise TypeError(f"Expected UserRecord, got {type(user)}")


# ─── POST /auth/login ────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Получить пару JWT токенов",
    responses={
        200: {"description": "Успешная аутентификация"},
        401: {"description": "Неверный логин или пароль"},
    },
)
async def login(
    body: LoginRequest,
    settings: Settings = Depends(get_settings),
    user_service: AbstractUserService = Depends(get_user_service),
) -> TokenResponse:
    user = await user_service.authenticate(body.username, body.password)
    if user is None:
        # Универсальное сообщение — не раскрываем, что именно неверно
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_CREDENTIALS", "message": "Invalid username or password"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("auth.login_success", user_id=user.user_id, username=user.username)
    return _build_token_response(user.user_id, UserRole(user.role), settings)


# ─── POST /auth/register ──────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserContext,
    status_code=status.HTTP_201_CREATED,
    summary="Зарегистрировать нового пользователя",
    responses={
        201: {"description": "Пользователь создан"},
        409: {"description": "Имя пользователя или email уже занято"},
        403: {"description": "Только администратор может назначить роль не-OPERATOR"},
    },
)
async def register(
    body: RegisterRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    user_service: AbstractUserService = Depends(get_user_service),
) -> UserContext:
    # Если запрашивается роль выше OPERATOR — нужны права ADMIN
    if body.role not in (UserRole.VIEWER, UserRole.OPERATOR):
        current_user_opt: UserContext | None = None
        try:
            from gateway_service.auth.middleware import get_current_user_optional
            current_user_opt = await get_current_user_optional(request)
        except Exception:
            pass

        if current_user_opt is None or current_user_opt.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "PERMISSION_DENIED",
                    "message": "Only admins can assign SUPERVISOR or ADMIN role",
                },
            )

    try:
        user = await user_service.create(
            username=body.username,
            email=body.email,
            password=body.password,
            role=body.role.value,
        )
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_code": "USER_ALREADY_EXISTS", "message": exc.message},
        ) from exc

    logger.info("auth.registered", username=user.username, role=user.role)
    return _user_record_to_context(user)


# ─── GET /auth/me ────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserContext,
    summary="Получить профиль текущего пользователя",
)
async def get_me(
    current_user: UserContext = Depends(get_current_user),
    user_service: AbstractUserService = Depends(get_user_service),
) -> UserContext:
    # Обновляем профиль из хранилища (токен содержит только user_id и role)
    record = await user_service.get_by_id(current_user.user_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "USER_NOT_FOUND", "message": "User not found"},
        )
    return _user_record_to_context(record)


# ─── PUT /auth/me ────────────────────────────────────────────────────────────

@router.put(
    "/me",
    response_model=UserContext,
    summary="Обновить профиль текущего пользователя",
)
async def update_me(
    body: UserUpdateRequest,
    current_user: UserContext = Depends(get_current_user),
    user_service: AbstractUserService = Depends(get_user_service),
) -> UserContext:
    try:
        record = await user_service.update(
            current_user.user_id,
            email=body.email,
            password=body.password,
            display_name=body.display_name,
        )
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "USER_NOT_FOUND", "message": exc.message},
        ) from exc
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_code": "USER_ALREADY_EXISTS", "message": exc.message},
        ) from exc

    logger.info("auth.profile_updated", user_id=current_user.user_id)
    return _user_record_to_context(record)


# ─── POST /auth/refresh ───────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Обновить access token по refresh token",
    responses={
        200: {"description": "Новая пара токенов"},
        401: {"description": "Refresh token недействителен или истёк"},
    },
)
async def refresh(
    body: RefreshRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    # Декодируем без проверки exp (чтобы дать понятную ошибку)
    payload = decode_token_unsafe(body.refresh_token, settings)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_TOKEN", "message": "Invalid refresh token"},
        )

    if payload.token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "WRONG_TOKEN_TYPE", "message": "Refresh token required"},
        )

    # Проверяем срок действия вручную
    if payload.exp < int(time.time()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "TOKEN_EXPIRED", "message": "Refresh token has expired"},
        )

    # Проверяем blacklist
    redis = getattr(request.app.state, "redis", None)
    if redis:
        try:
            in_blacklist = await redis.get(f"jwt:blacklist:{payload.jti}")
            if in_blacklist:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"error_code": "TOKEN_REVOKED", "message": "Refresh token has been revoked"},
                )
        except HTTPException:
            raise
        except Exception:
            pass

    # Добавляем старый refresh token в blacklist (rotation)
    remaining_ttl = max(0, payload.exp - int(time.time()))
    await add_token_to_blacklist(request, payload.jti, remaining_ttl + 60)

    # Выдаём новую пару
    logger.info("auth.token_refreshed", user_id=payload.sub)
    return _build_token_response(payload.sub, UserRole(payload.role), settings)


# ─── POST /auth/logout ────────────────────────────────────────────────────────

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Выйти (отозвать токен)",
)
async def logout(
    body: RefreshRequest,
    request: Request,
    current_user: UserContext = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> Response:
    # Добавляем refresh token в blacklist
    payload = decode_token_unsafe(body.refresh_token, settings)
    if payload and payload.token_type == "refresh":
        remaining_ttl = max(0, payload.exp - int(time.time()))
        await add_token_to_blacklist(request, payload.jti, remaining_ttl + 60)

    logger.info("auth.logout", user_id=current_user.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
