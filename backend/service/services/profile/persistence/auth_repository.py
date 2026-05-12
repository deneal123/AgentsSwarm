import logging
from typing import TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from service.models.db.db_models import UserSession
from service.shared.repositories.base_repository import BaseRepository
from service.shared.repositories.decorators.session_processor import connection

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from service.infrastructure.cache.redis_session_store import RedisSessionStore


class AuthRepository(BaseRepository):

    def __init__(
        self,
        connector,
        session_store: "RedisSessionStore | None" = None,
    ) -> None:
        super().__init__(connector)
        self._session_store = session_store

    @connection()
    async def create_session(
        self,
        user_session: UserSession,
        session: AsyncSession | None = None,
    ) -> UserSession:
        assert session is not None, "DB session is required"

        stmt = (
            select(UserSession.id)
            .where(UserSession.user_id == user_session.user_id)
            .with_for_update(skip_locked=True)
        )
        result = await session.execute(stmt)
        sessions_to_delete = result.scalars().all()

        if sessions_to_delete:
            logger.info(
                f"User already has sessions, deleting {len(sessions_to_delete)} old sessions"
            )
            del_stmt = delete(UserSession).where(UserSession.id.in_(sessions_to_delete))
            await session.execute(del_stmt)

        if self._session_store:
            await self._session_store.invalidate_user_sessions(user_session.user_id)

        logger.debug(f"Creating new session: {user_session}")
        session.add(instance=user_session)
        await session.flush()
        logger.debug(f"Session created: {user_session}")

        if self._session_store:
            await self._session_store.store_session(user_session)
        return user_session

    @connection()
    async def update_session(
        self, user_session: UserSession, session: AsyncSession | None = None
    ) -> UserSession:
        assert session is not None, "DB session is required"
        logger.debug(f"Updating session: {user_session}")
        await session.merge(user_session)
        await session.flush()
        logger.debug(f"Session updated: {user_session}")

        if self._session_store:
            await self._session_store.store_session(user_session)
        return user_session

    @connection()
    async def fetch_user_session(self, token: str, session: AsyncSession | None = None) -> UserSession | None:
        assert session is not None, "DB session is required"
        result = await session.execute(select(UserSession).where(UserSession.token == token))
        return result.scalar_one_or_none()

    @connection()
    async def insert_user_session(self, user_session: UserSession, session: AsyncSession | None = None) -> UserSession:
        assert session is not None, "DB session is required"
        session.add(user_session)
        await session.flush()
        return user_session
