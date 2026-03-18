import math
from typing import Any
from uuid import UUID

from argon2 import PasswordHasher
from service.models.db.user_models import User
from service.models.pydantic.profile import UserResponse
from service.repositories.exceptions import RepositoryNotFoundError
from service.repositories.profile_repository import ProfileRepository
from service.services.base_service import BaseService
from service.settings import ServersConfig
from service.utils.logging_decorators import log_operation


class ProfileService(BaseService[ProfileRepository]):
    """Service for managing user profiles with business logic."""

    PROFILE_MUTABLE_FIELDS = {"first_name", "last_name", "middle_name"}

    def __init__(
        self,
        repository: ProfileRepository,
        cache: Any | None = None,
        cache_ttl_seconds: int | None = None,
        server_config: ServersConfig | None = None,
    ) -> None:
        super().__init__(repository)
        self.ph = PasswordHasher()
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds
        self._server_config = server_config

    def _apply_admin_role(self, response: UserResponse) -> UserResponse:
        """Override role to 'admin' if user ID is listed in SERVERS__ADMIN_USER_IDS."""
        if self._server_config and str(response.id).lower() in self._server_config.admin_user_ids_set:
            response.role = "admin"
        return response

    @property
    def repository(self) -> ProfileRepository:
        return self.repo

    @log_operation(log_args=True)
    async def fetch_user_profile(self, user_id: UUID) -> UserResponse:
        """Fetch user profile by ID.

        Args:
            user_id: User UUID

        Returns:
            UserResponse with profile data

        Raises:
            RepositoryNotFoundError: If user not found
        """
        user = await self.repository.fetch_user_profile(user_id)
        self._validate_not_found(user, "User", user_id)

        return self._apply_admin_role(UserResponse.model_validate(user))

    @log_operation(log_args=True)
    async def fetch_user_profile_by_email(self, email: str) -> UserResponse | None:
        """Fetch user profile by email.

        Args:
            email: User email address

        Returns:
            UserResponse if found, None otherwise
        """
        user = await self.repository.fetch_user_by_email(email)
        if not user:
            return None

        return self._apply_admin_role(UserResponse.model_validate(user))

    async def fetch_user_with_credentials(self, email: str) -> User | None:
        """Fetch user entity including password hash."""
        self._log_operation("fetch_user_credentials", "User", email)
        return await self.repository.fetch_user_entity_by_email(email)

    @log_operation(log_args=True)
    async def create_new_user(
        self,
        email: str,
        password: str,
        first_name: str | None = None,
        last_name: str | None = None,
        timezone: str = "UTC",
    ) -> UserResponse:
        """Create new user with email and password.

        Args:
            email: User email
            password: Plain text password (will be hashed)

        Returns:
            UserResponse with created user data
        """
        password_hash = self.ph.hash(password)
        new_user = await self.repository.create_user(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            timezone=timezone,
        )
        return self._apply_admin_role(UserResponse.model_validate(new_user))

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash.

        Args:
            password: Plain text password
            password_hash: Argon2 hash

        Returns:
            True if password matches, False otherwise
        """
        ph = PasswordHasher()
        try:
            return ph.verify(password_hash, password)
        except Exception:
            return False

    @staticmethod
    def normalize_email(email: str) -> str:
        """Normalize email address.

        Args:
            email: Email address

        Returns:
            Normalized lowercase email without + aliases
        """
        local_part, domain_part = email.rsplit("@", 1)

        if "+" in local_part:
            local_part = local_part.split("+")[0]

        return f"{local_part}@{domain_part}".lower()

    @log_operation(log_args=True)
    async def update_profile(
        self, user_id: UUID, updates: dict[str, str | None]
    ) -> UserResponse:
        """Update mutable profile fields.

        Args:
            user_id: User UUID
            updates: Dictionary of fields to update

        Returns:
            UserResponse with updated data
        """
        fields_to_apply = {k: v for k, v in updates.items() if k in self.PROFILE_MUTABLE_FIELDS}
        if not fields_to_apply:
            return await self.fetch_user_profile(user_id)

        # Fetch current user
        user = await self.repository.fetch_user_profile(user_id)
        self._validate_not_found(user, "User", user_id)

        # Apply updates
        for field_name, value in fields_to_apply.items():
            setattr(user, field_name, value)

        updated_user = await self.repository.update_user_profile(user)

        self._log_operation("update_profile_completed", "User", user_id)
        return UserResponse.model_validate(updated_user)

    def calculate_profile_completeness(self, profile: UserResponse) -> int:
        """Score profile completeness based on required fields."""

        required_fields = ("first_name", "last_name", "email")
        filled = sum(bool(getattr(profile, field)) for field in required_fields)
        if not required_fields:
            return 0

        return math.floor((filled / len(required_fields)) * 100)

    @log_operation(log_args=True)
    async def verify_email(self, user_id: UUID) -> bool:
        """Mark user email as verified."""
        profile = await self.fetch_user_profile(user_id)
        self._validate_not_found(profile, "User", user_id)
        return await self.repository.verify_email(user_id)

    @log_operation(log_args=True, log_result=True)
    async def change_password(
        self, user_id: UUID, current_password: str, new_password: str
    ) -> bool:
        user = await self.repository.fetch_user_entity_by_id(user_id)
        self._validate_not_found(user, "User", user_id)

        if not user.password_hash or not self.verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")

        new_hash = self.ph.hash(new_password)
        updated = await self.repository.update_password(user_id, new_hash)
        if updated:
            # result logged by decorator already
            pass

        return updated

    @log_operation(log_args=True)
    async def update_preferences(self, user_id: UUID, preferences: dict[str, Any]) -> UserResponse:
        """Update user preferences stored in metadata."""
        return await self.repository.update_user_preferences(user_id, preferences)

    @log_operation(log_args=True)
    async def update_privacy_settings(
        self, user_id: UUID, privacy_settings: dict[str, Any]
    ) -> UserResponse:
        return await self.repository.update_privacy_settings(user_id, privacy_settings)

    @log_operation(log_args=True)
    async def delete_account(self, user_id: UUID) -> bool:
        success = await self.repository.deactivate_user(user_id)
        if not success:
            raise RepositoryNotFoundError("User", user_id)

        return True
