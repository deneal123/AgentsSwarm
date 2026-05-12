from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from service.infrastructure.database.postgresql import PgConnector


class BaseRepository:
    """Base repository class with shared helpers."""

    def __init__(self, connector: PgConnector) -> None:
        self._connector = connector

    @property
    def connector(self) -> PgConnector:
        return self._connector

    @asynccontextmanager
    async def session_scope(self) -> AsyncIterator[AsyncSession]:
        async with self._connector.get_session_context() as session:
            yield session

    async def _execute(self, session: AsyncSession, statement):
        return await session.execute(statement)
