import logging
from typing import TYPE_CHECKING
from uuid import UUID

from argon2 import PasswordHasher

from service.models.profile_models import UserProfileLogic
from service.services.profile.application.dto import (
    DeleteChatHistoryCommand,
    GetProfileOverviewQuery,
    ProfileOverviewResult,
    UpdateProfileCommand,
)
from service.services.profile.application.mappers import to_profile_overview_result
from service.services.profile.application.ports.interfaces import ProfileCachePort, ProfileRepositoryPort
from service.settings import ProfileConfig

logger = logging.getLogger(__name__)

PROFILE_BY_ID_NAMESPACE = "profile:id"
PROFILE_BY_EMAIL_NAMESPACE = "profile:email"
PROFILE_MUTABLE_FIELDS = {"first_name", "timezone", "avatar_url"}


class ProfileService:
    def __init__(
        self,
        config: ProfileConfig,
        repository: ProfileRepositoryPort,
        cache: ProfileCachePort | None = None,
        cache_ttl_seconds: int | None = None,
    ) -> None:
        self.config = config
        self.repository = repository
        self.ph = PasswordHasher()
        self.cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds

    async def _cache_profile(self, profile: UserProfileLogic) -> None:
        if not self.cache:
            return
        payload = profile.model_dump()
        await self.cache.set_json(
            PROFILE_BY_ID_NAMESPACE,
            str(profile.id),
            payload,
            ttl_seconds=self._cache_ttl_seconds,
        )
        await self.cache.set_json(
            PROFILE_BY_EMAIL_NAMESPACE,
            profile.email.lower(),
            payload,
            ttl_seconds=self._cache_ttl_seconds,
        )

    async def _get_cached_profile_by_id(self, user_id: UUID) -> UserProfileLogic | None:
        if not self.cache:
            return None
        cached = await self.cache.get_json(PROFILE_BY_ID_NAMESPACE, str(user_id))
        if not cached:
            return None
        try:
            return UserProfileLogic.model_validate(cached)
        except Exception:  # noqa: BLE001
            logger.warning("Invalid cached profile for user_id=%s; purging", user_id)
            await self.cache.invalidate(PROFILE_BY_ID_NAMESPACE, str(user_id))
            return None

    async def _get_cached_profile_by_email(self, email: str) -> UserProfileLogic | None:
        if not self.cache:
            return None
        cache_key = email.lower()
        cached = await self.cache.get_json(PROFILE_BY_EMAIL_NAMESPACE, cache_key)
        if not cached:
            return None
        try:
            return UserProfileLogic.model_validate(cached)
        except Exception:  # noqa: BLE001
            logger.warning("Invalid cached profile for email=%s; purging", email)
            await self.cache.invalidate(PROFILE_BY_EMAIL_NAMESPACE, cache_key)
            return None

    async def _invalidate_profile_cache(self, user_id: UUID, email: str) -> None:
        if not self.cache:
            return
        await self.cache.invalidate(PROFILE_BY_ID_NAMESPACE, str(user_id))
        await self.cache.invalidate(PROFILE_BY_EMAIL_NAMESPACE, email.lower())

    async def _refresh_profile_cache(
        self, profile: UserProfileLogic, previous_email: str | None = None
    ) -> None:
        if not self.cache:
            return
        if previous_email and previous_email.lower() != profile.email.lower():
            await self.cache.invalidate(PROFILE_BY_EMAIL_NAMESPACE, previous_email.lower())
        await self._cache_profile(profile)

    async def fetch_user_profile(self, user_id: UUID) -> UserProfileLogic:
        logger.info(f"Fetching profile for user: {user_id}")

        cached_profile = await self._get_cached_profile_by_id(user_id)
        if cached_profile:
            logger.debug("Profile cache hit for user_id=%s", user_id)
            return cached_profile

        user_profile = await self.repository.fetch_user_profile(str(user_id))
        if not user_profile:
            logger.error(f"User profile not found for user: {user_id}")
            raise ValueError("User profile not found")
        logger.debug(f"User profile: {user_profile}")

        await self._cache_profile(user_profile)

        return user_profile

    async def get_profile_overview(
        self, query: GetProfileOverviewQuery
    ) -> ProfileOverviewResult:
        profile = await self.fetch_user_profile(query.user_id)
        return to_profile_overview_result(profile)

    async def fetch_user_profile_by_email(self, email: str) -> UserProfileLogic | None:
        logger.info(f"Fetching profile for email: {email}")

        cached_profile = await self._get_cached_profile_by_email(email)
        if cached_profile:
            logger.debug("Profile cache hit for email=%s", email)
            return cached_profile

        user_profile = await self.repository.fetch_user_by_email(email)
        if user_profile:
            logger.debug(f"User profile: {user_profile}")
            await self._cache_profile(user_profile)
        else:
            logger.debug(f"User profile not found for email: {email}")

        return user_profile

    async def create_new_user(self, email: str, password: str) -> UserProfileLogic:
        logger.info(f"Creating new user with email: {email}")
        password_hash = self.ph.hash(password)
        new_user = await self.repository.create_user(
            email=email,
            password_hash=password_hash,
        )
        await self._cache_profile(new_user)
        return new_user

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            return self.ph.verify(password_hash, password)
        except Exception:
            return False

    async def update_profile_details(
        self, command: UpdateProfileCommand
    ) -> ProfileOverviewResult:
        updates = command.model_dump(exclude={"user_id"}, exclude_unset=True)
        logger.info("Updating profile for user_id=%s with fields=%s", command.user_id, list(updates.keys()))

        fields_to_apply = {k: v for k, v in updates.items() if k in PROFILE_MUTABLE_FIELDS}
        if not fields_to_apply:
            current = await self.fetch_user_profile(command.user_id)
            return to_profile_overview_result(current)

        profile = await self.fetch_user_profile(command.user_id)
        previous_email = profile.email

        for field_name, value in fields_to_apply.items():
            setattr(profile, field_name, value)

        updated_profile = await self.repository.update_user_profile(profile)
        await self._refresh_profile_cache(updated_profile, previous_email)

        logger.info("Profile updated for user_id=%s", command.user_id)
        return to_profile_overview_result(updated_profile)

    async def delete_chat_history(self, command: DeleteChatHistoryCommand) -> None:
        cached = await self._get_cached_profile_by_id(command.user_id)
        await self.repository.delete_user_chat_history(str(command.user_id))
        if cached:
            await self._invalidate_profile_cache(command.user_id, cached.email)
        logger.info("Deleted chat history for user=%s", command.user_id)
