"""User profile management endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from service.models.pydantic.auth import AuthProfile
from service.presentation.schemas.auth import UserResponse, UserUpdateRequest
from service.presentation.dependencies import (
    get_current_user,
    get_file_saver_service,
    get_profile_service,
    require_user,
)
from service.services.profile_service import ProfileService
from service.services.file_saver_service import FileSaverService

logger = logging.getLogger(__name__)

profile_router = APIRouter(prefix="/api/v1/profile", tags=["Profile"])


@profile_router.get(
    "/me",
    response_model=UserResponse,
    summary="Получить профиль текущего пользователя",
    description="Возвращает подробную информацию об аутентифицированном пользователе.",
)
async def get_my_profile(
    current_user: AuthProfile = Depends(require_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> UserResponse:
    """Get current user's profile."""
    return await profile_service.fetch_user_profile(current_user.user_id)


@profile_router.patch(
    "/me",
    response_model=UserResponse,
    summary="Обновить профиль текущего пользователя",
    description="Обновляет данные профиля. Изменяются только переданные поля.",
)
async def update_my_profile(
    updates: UserUpdateRequest,
    current_user: AuthProfile = Depends(require_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> UserResponse:
    """Update current user's profile."""
    return await profile_service.update_profile(
        current_user.user_id, updates.model_dump(exclude_unset=True)
    )



