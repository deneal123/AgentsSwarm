from uuid import UUID

from service.presentation.routers.profile_api.schemas import ProfileResponse, ProfileUpdateRequest
from service.services.profile.application.dto import (
    DeleteChatHistoryCommand,
    GetProfileOverviewQuery,
    ProfileOverviewResult,
    UpdateProfileCommand,
)


def to_get_profile_query(user_id: UUID) -> GetProfileOverviewQuery:
    return GetProfileOverviewQuery(user_id=user_id)


def to_update_profile_command(user_id: UUID, payload: ProfileUpdateRequest) -> UpdateProfileCommand:
    data = payload.model_dump(exclude_unset=True)
    return UpdateProfileCommand(user_id=user_id, **data)


def to_delete_chat_history_command(user_id: UUID) -> DeleteChatHistoryCommand:
    return DeleteChatHistoryCommand(user_id=user_id)


def to_profile_response(result: ProfileOverviewResult, permissions: list[str]) -> ProfileResponse:
    return ProfileResponse(
        id=result.id,
        email=result.email,
        first_name=result.first_name,
        company=result.company,
        timezone=result.timezone,
        avatar_url=result.avatar_url,
        created_at=result.created_at,
        updated_at=result.updated_at,
        permissions=permissions,
    )
