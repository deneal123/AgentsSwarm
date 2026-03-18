"""Repository for authentication and session management."""

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from service.models.db import GuestSession, UserSession
from service.models.enums import SessionStatus
from service.repositories.base_repository import BaseRepository
from service.repositories.decorators.decorators import cache, log_operation, validate_params
from service.repositories.decorators.session_processor import connection
from service.repositories.exceptions import RepositoryNotFoundError
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from service.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from service.infrastructure.cache.redis_session_store import RedisSessionStore


class AuthRepository(BaseRepository):
    """Repository for authentication and session management."""

    def __init__(
        self,
        connector,
        session_store: "RedisSessionStore | None" = None,
    ) -> None:
        super().__init__(connector)
        self._session_store = session_store


    @log_operation(log_level=logging.INFO)
    @connection()
    async def create_session(
        self,
        user_session: UserSession,
        session: AsyncSession | None = None,
    ) -> UserSession:
        """Create new user session."""
        assert session is not None, "DB session is required"

        logger.debug(f"Creating new session for user_id={user_session.user_id}")
        session.add(instance=user_session)
        await session.flush()

        if self._session_store:
            await self._session_store.store_session(user_session)

        logger.info(f"Session created: {user_session.id}")
        return user_session


    @log_operation(log_level=logging.DEBUG)
    @connection()
    async def update_session(
        self, user_session: UserSession, session: AsyncSession | None = None
    ) -> UserSession:
        """Update existing user session."""
        assert session is not None, "DB session is required"

        logger.debug(f"Updating session: {user_session.id}")
        await session.merge(user_session)
        await session.flush()

        if self._session_store:
            await self._session_store.store_session(user_session)

        logger.info(f"Session updated: {user_session.id}")
        return user_session


    @cache(ttl=60.0, namespace="auth_sessions")
    @connection()
    async def fetch_user_session(
        self, token: str, session: AsyncSession | None = None
    ) -> UserSession | None:
        """Fetch user session by token (cached)."""
        assert session is not None, "DB session is required"

        return await self.get_one_or_none(
            session=session,
            model=UserSession,
            filters={"token": token},
        )


    @connection()
    async def insert_user_session(
        self, user_session: UserSession, session: AsyncSession | None = None
    ) -> UserSession:
        """Insert new user session."""
        assert session is not None, "DB session is required"

        session.add(user_session)
        await session.flush()
        logger.info(f"User session inserted: {user_session.id}")
        return user_session


    @cache(ttl=60.0, namespace="auth_sessions")
    @connection()
    async def get_session_by_id(
        self, session_id: UUID, session: AsyncSession | None = None
    ) -> UserSession | None:
        """Get session by ID (cached)."""
        assert session is not None, "DB session is required"

        # Use BaseRepository's get_one_or_none
        return await self.get_one_or_none(
            session=session,
            model=UserSession,
            filters={"id": session_id},
        )


    @log_operation(log_level=logging.DEBUG)
    @cache(ttl=60.0, namespace="auth_sessions")
    @connection()
    async def get_session_by_refresh_token(
        self, refresh_token: str, session: AsyncSession | None = None
    ) -> UserSession | None:
        """Get session by refresh token (cached)."""
        assert session is not None, "DB session is required"

        return await self.get_one_or_none(
            session=session,
            model=UserSession,
            filters={"refresh_token": refresh_token},
        )


    @log_operation(log_level=logging.DEBUG)
    @connection()
    async def revoke_session(self, session_id: UUID, session: AsyncSession | None = None) -> bool:
        """Revoke user session by ID."""
        assert session is not None, "DB session is required"

        logger.debug(f"Revoking session: {session_id}")
        stmt = (
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(status=SessionStatus.REVOKED)
        )
        result = await session.execute(stmt)
        await session.flush()

        if self._session_store and result.rowcount > 0:
            await self._session_store.invalidate_session(session_id)

        if result.rowcount > 0:
            logger.info(f"Session revoked: {session_id}")
        else:
            logger.warning(f"Session not found for revocation: {session_id}")

        return result.rowcount > 0


    @log_operation(log_level=logging.DEBUG)
    @connection()
    async def revoke_all_user_sessions(
        self, user_id: UUID, session: AsyncSession | None = None
    ) -> int:
        """Revoke all active sessions for a user."""
        assert session is not None, "DB session is required"

        logger.debug(f"Revoking all sessions for user: {user_id}")
        stmt = (
            update(UserSession)
            .where(UserSession.user_id == user_id)
            .where(UserSession.status != SessionStatus.REVOKED)
            .values(status=SessionStatus.REVOKED)
        )
        result = await session.execute(stmt)
        await session.flush()

        if self._session_store and result.rowcount > 0:
            await self._session_store.invalidate_user_sessions(user_id)

        count = result.rowcount
        logger.info(f"Revoked {count} sessions for user: {user_id}")
        return count


    @log_operation(log_level=logging.DEBUG)
    @connection()
    async def cleanup_expired_sessions(self, session: AsyncSession | None = None) -> int:
        """Delete expired sessions from database."""
        assert session is not None, "DB session is required"

        logger.debug("Cleaning up expired sessions")
        stmt = delete(UserSession).where(UserSession.status == SessionStatus.EXPIRED)
        result = await session.execute(stmt)
        await session.flush()

        count = result.rowcount
        logger.info(f"Cleaned up {count} expired sessions")
        return count


    @connection()
    async def update_session_status(
        self, session_id: UUID, status: SessionStatus, session: AsyncSession | None = None
    ) -> bool:
        """Update session status."""
        assert session is not None, "DB session is required"

        logger.debug(f"Updating session {session_id} to status: {status}")
        stmt = update(UserSession).where(UserSession.id == session_id).values(status=status)
        result = await session.execute(stmt)
        await session.flush()

        if self._session_store and result.rowcount > 0:
            user_session = await self.get_session_by_id(session_id=session_id, session=session)
            if user_session:
                await self._session_store.store_session(user_session)

        if result.rowcount > 0:
            logger.info(f"Session status updated: {session_id} -> {status}")
        else:
            logger.warning(f"Session not found for status update: {session_id}")

        return result.rowcount > 0


    @log_operation(log_level=logging.INFO)
    @connection()
    async def create_guest_session(
        self, guest_session: GuestSession, session: AsyncSession | None = None
    ) -> GuestSession:
        """Create new guest session."""
        assert session is not None, "DB session is required"

        logger.debug(f"Creating guest session: {guest_session.id}")
        session.add(guest_session)
        await session.flush()

        logger.info(f"Guest session created: {guest_session.id}")
        return guest_session


    @cache(ttl=60.0, namespace="guest_sessions")
    @connection()
    async def get_guest_session_by_id(
        self, session_id: UUID, session: AsyncSession | None = None
    ) -> GuestSession | None:
        """Get guest session by ID (cached)."""
        assert session is not None, "DB session is required"

        # Use BaseRepository's get_one_or_none
        return await self.get_one_or_none(
            session=session,
            model=GuestSession,
            filters={"id": session_id},
        )
        return result.scalar_one_or_none()

    @log_operation(log_level=logging.DEBUG)
    @connection()
    async def convert_guest_to_user_session(
        self,
        guest_session_id: UUID,
        user_session: UserSession,
        session: AsyncSession | None = None,
    ) -> UserSession:
        """Convert guest session into authenticated user session."""
        assert session is not None, "DB session is required"

        guest = await session.get(GuestSession, guest_session_id)
        if guest is None:
            raise RepositoryNotFoundError(f"Guest session not found: {guest_session_id}")

        guest.converted_to_user_id = user_session.user_id
        session.add(user_session)
        await session.flush()

        if self._session_store:
            await self._session_store.store_session(user_session)

        logger.info(
            "Converted guest session %s to user %s",
            guest_session_id,
            user_session.user_id,
        )
        return user_session
