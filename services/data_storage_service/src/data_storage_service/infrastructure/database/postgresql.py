import asyncio
import logging
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from service.settings import PostgresqlConfig

logger = logging.getLogger(__name__)


class PgConnector:
    _engine: AsyncEngine | None = None
    _session_maker: async_sessionmaker | None = None
    _bound_loop: asyncio.AbstractEventLoop | None = None

    def __init__(self, config: PostgresqlConfig, force_new: bool = False) -> None:
        self.config = config
        self._force_new = force_new
        self._engine = self._get_engine()
        self._session_maker = self._get_session_maker()

    def _get_engine(self) -> AsyncEngine:
        if self._force_new:
            return create_async_engine(
                self.config.dsn,
                echo=self.config.db_echo,
                echo_pool=self.config.db_echo,
                pool_size=self.config.db_pool_size,
                max_overflow=self.config.db_max_overflow,
                pool_timeout=self.config.db_pool_timeout,
                pool_recycle=self.config.db_pool_recycle,
                # Disable pre-ping for task-scoped engines: the pool is brand-new
                # and pre-ping's async ping would run in the wrong loop otherwise.
                pool_pre_ping=False,
                future=True,
            )

        try:
            current_loop = asyncio.get_event_loop()
        except RuntimeError:
            current_loop = None

        if PgConnector._engine is not None and PgConnector._bound_loop != current_loop:
            try:
                PgConnector._engine = None
                PgConnector._session_maker = None
            except Exception as e:
                logger.debug("Failed to dispose previous engine: %s", e, exc_info=True)

        if not PgConnector._engine:
            PgConnector._engine = create_async_engine(
                self.config.dsn,
                echo=self.config.db_echo,
                echo_pool=self.config.db_echo,
                pool_size=self.config.db_pool_size,
                max_overflow=self.config.db_max_overflow,
                pool_timeout=self.config.db_pool_timeout,
                pool_recycle=self.config.db_pool_recycle,
                pool_pre_ping=self.config.db_pool_pre_ping,
                future=True,
            )
            PgConnector._bound_loop = current_loop
        return PgConnector._engine

    def _get_session_maker(self) -> async_sessionmaker:
        if self._force_new:
            # Must create a fresh session maker bound to the fresh engine.
            # Do NOT touch the class-level cache so the shared singleton
            # (used by FastAPI) is left untouched.
            return async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
        if not PgConnector._session_maker:
            PgConnector._session_maker = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
        return PgConnector._session_maker

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session for use as FastAPI dependency"""
        if self._session_maker is None:
            logger.error("Attempted to get session but sessionmaker is not initialized")
            raise ValueError("PostgreSQL sessionmaker is not initialized")
        try:
            async with self._session_maker() as session:
                yield session
        except Exception as e:
            logger.exception(f"Error managing database session: {e}")
            raise

    def get_session_context(self) -> AsyncSession:
        """Returns context manager for use outside FastAPI dependency injection."""
        if self._session_maker is None:
            logger.error("Attempted to get session context but sessionmaker is not initialized")
            raise ValueError("PostgreSQL sessionmaker is not initialized")
        return self._session_maker()

    async def verify_connection(self) -> None:
        """Open a short session and execute a trivial statement to verify connectivity."""
        if self._engine is None:
            raise ValueError("PostgreSQL engine is not initialized")
        try:
            async with self.get_session_context() as session:
                await session.execute(text("SELECT 1"))
                await session.commit()
        except Exception as e:
            logger.exception("Failed to verify PostgreSQL connection: %s", e)
            raise

    async def close(self) -> None:
        """Dispose engine connections gracefully."""
        try:
            if self._engine is not None:
                await self._engine.dispose()
        except Exception as e:
            logger.exception("Error disposing PostgreSQL engine: %s", e)
