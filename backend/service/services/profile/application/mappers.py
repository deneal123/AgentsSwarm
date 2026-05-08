from service.models.profile_models import UserProfileLogic
from service.services.profile.application.dto import ProfileOverviewResult


def to_profile_overview_result(profile: UserProfileLogic) -> ProfileOverviewResult:
    return ProfileOverviewResult(
        id=profile.id,
        email=profile.email,
        first_name=profile.first_name,
        company=profile.company,
        timezone=profile.timezone,
        avatar_url=profile.avatar_url,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
