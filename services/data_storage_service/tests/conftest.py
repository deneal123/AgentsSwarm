"""Фикстуры для тестов репозиториев."""

from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from tests.decorator_mocks import (
    RepositoryDecoratorMocks,
    patch_repository_decorators,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
os.environ.setdefault("LOG_DIR", str(ROOT_DIR / "logs"))
sys.path.insert(0, str(ROOT_DIR))

from service.repositories.decorators import set_redis_cache


class InMemoryRedisCache:
    """Простая замена Redis для локального кэширования."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], dict[str, object]] = {}

    async def get_json(self, namespace: str, identifier: str) -> dict[str, object] | None:
        return self._store.get((namespace, identifier))

    async def set_json(
        self,
        namespace: str,
        identifier: str,
        payload: dict[str, object],
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        self._store[(namespace, identifier)] = payload

    async def delete(self, namespace: str, identifier: str) -> None:
        self._store.pop((namespace, identifier), None)


class MemoryPgConnector:
    """Минимальный коннектор для тестов, повторяющий интерфейс PgConnector."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._session_maker = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
        )

    def get_session_context(self) -> AsyncSession:
        return self._session_maker()

@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def pg_connector(test_engine: AsyncEngine) -> MemoryPgConnector:
    return MemoryPgConnector(test_engine)


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    session_maker = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with session_maker() as session:
        transaction = await session.begin()
        try:
            yield session
        finally:
            await transaction.rollback()


@pytest.fixture(scope="session", autouse=True)
def configure_cache() -> InMemoryRedisCache:
    cache = InMemoryRedisCache()
    set_redis_cache(cache)
    return cache


@pytest.fixture
def decorator_mocks(monkeypatch) -> RepositoryDecoratorMocks:
    """Patch repository decorators to noop mocks for targeted tests."""
    return patch_repository_decorators(monkeypatch)
