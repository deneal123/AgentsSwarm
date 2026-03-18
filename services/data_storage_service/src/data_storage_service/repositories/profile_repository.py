"""Repository for user profile management in Pushi platform."""

import logging
from typing import Any
from uuid import UUID

from service.models.db import User, UserLaunch
from service.models.pydantic import UserProfileLogic, UserResponse
from service.repositories.base_repository import BaseRepository
from service.repositories.decorators.decorators import cache, log_operation, validate_params
from service.repositories.decorators.session_processor import connection
from service.repositories.exceptions import RepositoryNotFoundError, raise_not_found
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from service.utils.logger import get_logger

logger = get_logger(__name__)


class ProfileRepository(BaseRepository):
    """Repository for user profile management in Pushi platform."""

    @log_operation(log_level=logging.INFO)
    @validate_params(email=lambda x: "@" in x and len(x) >= 5)
    @connection()
    async def create_user(
        self,
        email: str,
        password_hash: str,
        first_name: str | None = None,
        last_name: str | None = None,
        timezone: str = "UTC",
        role: str = "lawyer",
        session: AsyncSession | None = None,
    ) -> UserResponse:
        """Create new user for Pushi platform."""
        assert session is not None, "DB session is required"

        new_user = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            timezone=timezone,
            role=role,
        )
        logger.debug(f"Creating user: {email}")

        session.add(new_user)
        await session.flush()

        logger.info(f"User created: {new_user.id}")
        return UserResponse.model_validate(new_user)


    @cache(ttl=120.0, namespace="user_profiles")
    @connection()
    async def fetch_user_profile(
        self, user_id: UUID, session: AsyncSession | None = None
    ) -> UserResponse | None:
        """Fetch user profile by ID (cached)."""
        assert session is not None, "DB session is required"

        logger.debug(f"Fetching user profile: {user_id}")

        db_user = await self.get_one_or_none(
            session=session,
            model=User,
            filters={"id": user_id},
        )

        if db_user:
            profile = UserResponse.model_validate(db_user)
            logger.debug(f"User profile found: {user_id}")
            return profile

        logger.debug(f"User profile not found: {user_id}")
        return None


    @cache(ttl=120.0, namespace="users")
    @connection()
    async def fetch_user_by_email(
        self, email: str, session: AsyncSession | None = None
    ) -> UserResponse | None:
        """Fetch user by email (cached)."""
        assert session is not None, "DB session is required"

        logger.debug(f"Fetching user by email: {email}")

        db_user = await self.get_one_or_none(
            session=session,
            model=User,
            filters={"email": email},
        )

        if db_user:
            profile = UserResponse.model_validate(db_user)
            logger.debug(f"User found by email: {email}")
            return profile

        logger.debug(f"User not found for email: {email}")
        return None

    @cache(ttl=120.0, namespace="users")
    @connection()
    async def fetch_user_entity_by_email(
        self, email: str, session: AsyncSession | None = None
    ) -> User | None:
        """Fetch full user entity by email (no caching)."""
        assert session is not None, "DB session is required"

        return await self.get_one_or_none(
            session=session,
            model=User,
            filters={"email": email},
        )

    @connection()
    async def fetch_user_entity_by_id(
        self, user_id: UUID, session: AsyncSession | None = None
    ) -> User | None:
        """Fetch full user entity by ID (no caching)."""
        assert session is not None, "DB session is required"

        return await self.get_one_or_none(
            session=session,
            model=User,
            filters={"id": user_id},
        )

    @connection()
    async def update_user_profile(
        self, user: UserProfileLogic, session: AsyncSession | None = None
    ) -> UserResponse:
        """Update user profile."""
        assert session is not None, "DB session is required"

        logger.debug(f"Updating user profile: {user.id}")

        payload = user.model_dump(exclude_unset=True)
        update_values = {
            k: v for k, v in payload.items() if k not in ["id", "created_at", "updated_at"]
        }

        stmt = update(User).where(User.id == user.id).values(**update_values).returning(User)
        result = await session.execute(stmt)
        db_user = result.scalar_one_or_none()

        if not db_user:
            raise_not_found(User, user.id, "id")

        updated_user = UserResponse.model_validate(db_user)
        logger.info(f"User profile updated: {user.id}")
        return updated_user

    @connection()
    async def verify_email(self, user_id: UUID, session: AsyncSession | None = None) -> bool:
        """Mark user email as verified."""
        assert session is not None, "DB session is required"

        logger.debug(f"Verifying email for user: {user_id}")
        stmt = update(User).where(User.id == user_id).values(email_verified=True)
        result = await session.execute(stmt)
        await session.flush()

        success = result.rowcount > 0
        if success:
            logger.info(f"Email verified for user: {user_id}")

        return success

    @connection()
    async def count_user_launches(self, user_id: UUID, session: AsyncSession | None = None) -> int:
        assert session is not None, "DB session is required"

        stmt = select(func.count()).select_from(UserLaunch).where(UserLaunch.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one() or 0

    @connection()
    async def count_user_sessions(self, user_id: UUID, session: AsyncSession | None = None) -> int:
        assert session is not None, "DB session is required"

        stmt = select(func.count()).select_from(UserSession).where(UserSession.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one() or 0

    @connection()
    async def update_password(
        self, user_id: UUID, password_hash: str, session: AsyncSession | None = None
    ) -> bool:
        assert session is not None, "DB session is required"

        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(password_hash=password_hash)
            .returning(User)
        )
        result = await session.execute(stmt)
        await session.flush()

        return result.rowcount > 0

    @connection()
    async def deactivate_user(self, user_id: UUID, session: AsyncSession | None = None) -> bool:
        assert session is not None, "DB session is required"

        stmt = update(User).where(User.id == user_id).values(is_active=False)
        result = await session.execute(stmt)
        await session.flush()

        return result.rowcount > 0
