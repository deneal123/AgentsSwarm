"""Profile API: user overview, updates, quota preview."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from service.presentation.dependencies import providers
from service.models.auth_models import AuthProfile
from service.presentation.dependencies.auth_checker import check_auth
from service.presentation.routers.profile_api.mappers import (
    to_delete_chat_history_command,
    to_get_profile_query,
    to_profile_response,
    to_update_profile_command,
)
from service.presentation.routers.profile_api.schemas import ProfileResponse, ProfileUpdateRequest
from service.services.profile.application.profile_service import ProfileService
from service.settings import config

logger = logging.getLogger(__name__)

profile_router = APIRouter(prefix="/api/profile")



@profile_router.get("/me", response_model=ProfileResponse)
async def get_profile(
    auth_profile: Annotated[AuthProfile, Depends(check_auth)],
    service: Annotated[ProfileService, Depends(providers.get_profile_service)],
) -> ProfileResponse:
    try:
        result = await service.get_profile_overview(to_get_profile_query(auth_profile.user_id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    permissions: list[str] = []
    if str(result.id).lower() in config.service.admin_user_ids_set:
        permissions.append("datasets:cleanup")
    return to_profile_response(result, permissions)


@profile_router.patch("/me", response_model=ProfileResponse)
async def update_profile(
    payload: ProfileUpdateRequest,
    auth_profile: Annotated[AuthProfile, Depends(check_auth)],
    service: Annotated[ProfileService, Depends(providers.get_profile_service)],
) -> ProfileResponse:
    try:
        overview = await service.update_profile_details(
            to_update_profile_command(auth_profile.user_id, payload)
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    permissions: list[str] = []
    if str(overview.id).lower() in config.service.admin_user_ids_set:
        permissions.append("datasets:cleanup")
    return to_profile_response(overview, permissions)


@profile_router.delete("/me/chat-history", status_code=204)
async def delete_my_chat_history(
    auth_profile: Annotated[AuthProfile, Depends(check_auth)],
    service: Annotated[ProfileService, Depends(providers.get_profile_service)],
) -> None:
    """Allow authenticated user to delete their chat history."""
    try:
        await service.delete_chat_history(to_delete_chat_history_command(auth_profile.user_id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return None


