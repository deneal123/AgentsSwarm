import logging

from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from service.models.db.db_models import User
from service.models.profile_models import UserProfileLogic
from service.repositories.base_repository import BaseRepository
from service.repositories.decorators.session_processor import connection
from service.repositories.exceptions import RepositoryNotFoundError

logger = logging.getLogger(__name__)


class ProfileRepository(BaseRepository):

    @connection()
    async def create_user(
        self,
        email: str,
        password_hash: str,
        session: AsyncSession | None = None,
    ) -> UserProfileLogic:
        assert session is not None, "DB session is required"

        new_user = User(
            email=email,
            password_hash=password_hash,
            available_launches=10,
        )
        logger.debug(f"Creating entity: {new_user}")
        session.add(new_user)
        await session.flush()
        logger.debug(f"Entity created: {new_user}")

        return UserProfileLogic.model_validate(new_user)

    @connection()
    async def fetch_user_profile(
        self, user_id: str, session: AsyncSession | None = None
    ) -> UserProfileLogic | None:
        assert session is not None, "DB session is required"
        logger.debug(f"Fetching user profile by id: {user_id}")

        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        db_user = result.scalar_one_or_none()

        if db_user:
            profile = UserProfileLogic.model_validate(db_user)
            logger.debug(f"Fetch result: {profile.model_dump_json(indent=4)}")
            return profile
        logger.debug(f"User profile not found for: {user_id=}")
        return None

    @connection()
    async def fetch_user_by_email(
        self, email: str, session: AsyncSession | None = None
    ) -> UserProfileLogic | None:
        assert session is not None, "DB session is required"
        logger.debug(f"Fetching user by email: {email}")

        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        db_user = result.scalar_one_or_none()

        if db_user:
            profile = UserProfileLogic.model_validate(db_user)
            logger.debug(f"Fetch result: {profile.model_dump_json(indent=4)}")
            return profile
        logger.debug(f"User not found for email: {email}")
        return None

    @connection()
    async def update_user_profile(
        self, user: UserProfileLogic, session: AsyncSession | None = None
    ) -> UserProfileLogic:
        assert session is not None, "DB session is required"
        logger.debug(f"Updating user profile: {user.model_dump_json(indent=4)}")

        payload = user.model_dump()
        update_values = {
            "email": payload["email"],
            "password_hash": payload["password_hash"],
            "first_name": payload.get("first_name"),
            "timezone": payload.get("timezone"),
            "avatar_url": payload.get("avatar_url"),
        }

        stmt = (
            update(User)
            .where(User.id == payload["id"])
            .values(**update_values)
            .returning(User)
        )
        result = await session.execute(stmt)
        db_user = result.scalar_one_or_none()

        if not db_user:
            raise RepositoryNotFoundError("User not found")

        updated_user = UserProfileLogic.model_validate(db_user)
        logger.debug(f"Updated user profile: {updated_user.model_dump_json(indent=4)}")
        return updated_user

    @connection()
    async def delete_user_chat_history(
        self, user_id: str, session: AsyncSession | None = None
    ) -> None:
        assert session is not None, "DB session is required"
        await session.execute(
            text(
                "DELETE FROM profile.chat_messages WHERE thread_id IN (SELECT id "
                "FROM profile.chat_threads WHERE user_id = :uid)"
            ),
            {"uid": user_id},
        )
        await session.execute(
            text("DELETE FROM profile.chat_threads WHERE user_id = :uid"),
            {"uid": user_id},
        )
