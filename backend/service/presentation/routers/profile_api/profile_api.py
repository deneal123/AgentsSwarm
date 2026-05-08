"""Profile API: user overview, updates, quota preview."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from service import container
from service.models.auth_models import AuthProfile
from service.models.profile_models import UserProfileLogic
from service.presentation.dependencies.auth_checker import check_auth
from service.presentation.routers.profile_api.schemas import (
    ProfileResponse,
    ProfileUpdateRequest,
)
from service.services.profile.application.profile_service import ProfileService
from service.settings import config

logger = logging.getLogger(__name__)

profile_router = APIRouter(prefix="/api/profile")


def _build_profile_response(
    profile: UserProfileLogic,
) -> ProfileResponse:
    permissions: list[str] = []
    if str(profile.id).lower() in config.service.admin_user_ids_set:
        permissions.append("datasets:cleanup")

    return ProfileResponse(
        id=profile.id,
        email=profile.email,
        first_name=profile.first_name,
        company=profile.company,
        timezone=profile.timezone,
        avatar_url=profile.avatar_url,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        permissions=permissions,
    )


@profile_router.get("/me", response_model=ProfileResponse)
async def get_profile(
    auth_profile: Annotated[AuthProfile, Depends(check_auth)],
    service: Annotated[ProfileService, Depends(container.get_profile_service)],
) -> ProfileResponse:
    try:
        result = await service.get_profile_overview(auth_profile.user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    return _build_profile_response(result)


@profile_router.patch("/me", response_model=ProfileResponse)
async def update_profile(
    payload: ProfileUpdateRequest,
    auth_profile: Annotated[AuthProfile, Depends(check_auth)],
    service: Annotated[ProfileService, Depends(container.get_profile_service)],
) -> ProfileResponse:
    try:
        await service.update_profile_details(
            auth_profile.user_id, payload.model_dump(exclude_unset=True)
        )
        overview = await service.get_profile_overview(auth_profile.user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    return _build_profile_response(overview)


@profile_router.delete("/me/chat-history", status_code=204)
async def delete_my_chat_history(
    auth_profile: Annotated[AuthProfile, Depends(check_auth)],
    service: Annotated[ProfileService, Depends(container.get_profile_service)],
) -> None:
    """Allow authenticated user to delete their chat history."""
    try:
        await service.delete_chat_history(auth_profile.user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return None



