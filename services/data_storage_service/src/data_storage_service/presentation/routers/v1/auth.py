import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from service.models.db.session_models import GuestSession
from service.models.pydantic.auth import AuthProfile
from service.presentation.schemas.auth import (
    GuestTokenResponse,
    LoginResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    UserUpdateRequest,
)
from service.presentation.dependencies import get_auth_service, get_profile_service
from service.presentation.dependencies.auth import get_current_user_optional
from service.services.auth_service import AuthService
from service.services.profile_service import ProfileService
from service.settings import config

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@auth_router.post(
    "/register",
    response_model=UserResponse,
    summary="Регистрация нового пользователя",
    description="Создаёт новый аккаунт по email и паролю. После регистрации необходимо выполнить вход отдельным запросом.",
)
async def register(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    profile_service: ProfileService = Depends(get_profile_service),
    request_body: UserRegisterRequest = Body(...),
) -> UserResponse:
    """Register a new user."""
    # Validate password strength
    auth_service.validate_password_strength(request_body.password)

    normalized_email = ProfileService.normalize_email(request_body.email)

    # Check for duplicate email
    existing = await profile_service.fetch_user_profile_by_email(normalized_email)
    if existing:
        from fastapi import HTTPException, status as http_status
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    user = await profile_service.create_new_user(
        email=normalized_email,
        password=request_body.password,
        first_name=request_body.first_name,
        last_name=request_body.last_name,
        timezone=request_body.timezone,
    )

    logger.info(f"User registered: {user.email}")
    return user


@auth_router.post(
    "/login",
    response_model=LoginResponse,
    summary="Вход по email и паролю",
    description="Аутентификация пользователя. Возвращает JWT access- и refresh-токены, устанавливает httpOnly cookie.",
)
async def login(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    request_body: UserLoginRequest = Body(...),
) -> LoginResponse:
    """Authenticate user and return JWT tokens."""
    user_agent = request.headers.get("user-agent", "unknown")

    # Authenticate user
    login_result = await auth_service.login(
        user_agent=user_agent,
        request_body=request_body,
    )

    # Set secure cookie with access token
    secure_cookie = not config.auth.dev_mode
    response.set_cookie(
        key="auth_token",
        value=login_result.access_token,
        httponly=True,
        secure=secure_cookie,
        samesite="strict" if secure_cookie else "lax",
        max_age=int(config.auth.jwt_exp_hours * 3600),
        path="/",
    )

    logger.info(f"User logged in: {request_body.email}")
    return login_result


@auth_router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="Обновление access-токена",
    description="Выдаёт новый access-токен по действующему refresh-токену.",
)
async def refresh_token(
    auth_service: AuthService = Depends(get_auth_service),
    request_body: TokenRefreshRequest = Body(...),
) -> TokenRefreshResponse:
    """Refresh JWT access token."""
    return await auth_service.refresh_token(request_body)


@auth_router.post(
    "/logout",
    summary="Завершение сессии",
    description="Инвалидирует текущую сессию пользователя и очищает auth-cookie.",
)
async def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: AuthProfile | None = Depends(get_current_user_optional),
):
    """Logout user: revoke DB session and clear cookie."""
    # Revoke session in DB by token from cookie if user is authenticated
    if current_user and current_user.type.value != "guest":
        auth_token = request.cookies.get("auth_token")
        if auth_token:
            try:
                session = await auth_service.repository.fetch_user_session(auth_token)
                if session:
                    await auth_service.repository.revoke_session(session.id)
            except Exception:
                pass  # Best-effort revocation

    response.delete_cookie(key="auth_token", path="/")
    logger.info("User logged out")
    return {"message": "Logged out successfully"}


# ---------------------------------------------------------------------------
# Guest session
# ---------------------------------------------------------------------------

class GuestTokenResponse(BaseModel):
    """Response with a stable guest session token."""
    guest_token: str
    guest_session_id: UUID
    expires_at: datetime


@auth_router.post(
    "/guest",
    response_model=GuestTokenResponse,
    summary="Создание гостевой сессии",
    description=(
        "Создаёт постоянный токен гостевой сессии. "
        "Передавайте полученный `guest_token` как cookie `auth_token` в последующих запросах, "
        "чтобы сохранять анонимную идентификацию (например, для просмотра своих задач в playground). "
        "Гостевые сессии действуют 7 дней."
    ),
    status_code=status.HTTP_201_CREATED,
)
async def create_guest_session(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> GuestTokenResponse:
    """Create or renew a guest session."""
    fingerprint = request.headers.get("X-Fingerprint")
    ip_address = request.client.host if request.client else None
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    token = secrets.token_urlsafe(32)

    guest = GuestSession(
        session_token=token,
        fingerprint=fingerprint,
        ip_address=ip_address,
        expires_at=expires_at,
    )
    created = await auth_service.repository.create_guest_session(guest)

    # Set as cookie so browser clients get it automatically
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=not config.auth.dev_mode,
        samesite="strict" if not config.auth.dev_mode else "lax",
        max_age=7 * 24 * 3600,
        path="/",
    )

    logger.info(f"Guest session created: {created.id}")
    return GuestTokenResponse(
        guest_token=token,
        guest_session_id=created.id,
        expires_at=expires_at,
    )
