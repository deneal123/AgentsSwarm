from uuid import uuid4

import jwt
from fastapi import Cookie, Depends, HTTPException, status

from service.models.enums import UserRole, UserType
from service.models.pydantic.auth import AuthProfile
from service.settings import config


async def _get_profile_service():
    """Lazy import to avoid circular dependencies."""
    from service.presentation.dependencies.services import get_profile_service

    return get_profile_service


def get_current_user(auth_token: str = Cookie(None)) -> AuthProfile:
    """Проверяет JWT из secure cookie 'auth_token'.

    Если токен отсутствует, создает guest сессию для доступа к публичным ресурсам.
    """
    if not auth_token:
        return AuthProfile(
            user_id=uuid4(),
            fingerprint=None,
            type=UserType.GUEST,
        )

    try:
        payload: dict = jwt.decode(
            auth_token, config.auth.secret, algorithms=[config.auth.algorithm]
        )

        # Be defensive: some older tokens may miss the 'type' claim.
        type_value = payload.get("type", UserType.REGISTERED_USER)
        try:
            user_type = UserType(type_value)
        except ValueError:
            user_type = UserType.REGISTERED_USER

        user_profile = AuthProfile(
            user_id=payload.get("sub"),
            fingerprint=payload.get("fingerprint"),
            type=user_type,
        )

        return user_profile
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_user_optional(auth_token: str = Cookie(None)) -> AuthProfile | None:
    """Возвращает пользователя из JWT или None для публичных endpoints."""
    try:
        return get_current_user(auth_token)
    except HTTPException:
        return None


def require_user(current_user: AuthProfile = Depends(get_current_user)) -> AuthProfile:
    """Требует аутентифицированного зарегистрированного пользователя (не guest)."""
    if current_user.type == UserType.GUEST:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return current_user


async def require_admin(current_user: AuthProfile = Depends(get_current_user)) -> AuthProfile:
    """Требует аутентифицированного пользователя с ролью admin.

    Async dependency — безопасно для FastAPI event loop.
    """
    if current_user.type == UserType.GUEST:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    from service import container

    profile_service = container.get(container.ProfileServiceName)
    user = await profile_service.fetch_user_profile(current_user.user_id)

    if not user or getattr(user, "role", None) != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Admin access required")

    return current_user


def get_current_active_user(current_user: AuthProfile = Depends(get_current_user)) -> AuthProfile:
    """Get current authenticated active user (alias for require_user)."""
    if current_user.type == UserType.GUEST:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return current_user


def get_current_user_or_guest(current_user: AuthProfile = Depends(get_current_user)) -> dict:
    """Get current user (registered or guest) and return appropriate IDs.
    
    Returns dict with either user_id or guest_session_id set.
    Used for endpoints that support both authenticated users and guests.
    """
    if current_user.type == UserType.GUEST:
        return {
            "user_id": None,
            "guest_session_id": current_user.user_id,  # Use user_id as guest_session_id
            "is_guest": True,
        }
    else:
        return {
            "user_id": current_user.user_id,
            "guest_session_id": None,
            "is_guest": False,
        }


def get_guest_session_optional(current_user: AuthProfile | None = Depends(get_current_user_optional)) -> dict | None:
    """Get guest session if present, None otherwise.
    
    Used for optional guest session support in demo endpoints.
    """
    if current_user is None:
        return None
    
    if current_user.type == UserType.GUEST:
        return {
            "guest_session_id": current_user.user_id,
            "is_guest": True,
        }
    
    return {
        "user_id": current_user.user_id,
        "is_guest": False,
    }
