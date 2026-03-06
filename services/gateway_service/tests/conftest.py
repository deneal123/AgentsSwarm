"""
Pytest fixtures для Gateway Service.

conftest.py — доступны во всех тестах автоматически.

Фикстуры:
  test_settings          — Settings без внешних сервисов
  mock_redis             — AsyncMock RedisClient
  mock_rabbitmq          — AsyncMock RabbitMQPublisher
  mock_grpc              — AsyncMock OrchestratorGrpcClient
  app                    — FastAPI (без реального lifespan)
  client                 — httpx AsyncClient (ASGITransport)
  operator_token         — JWT OPERATOR
  admin_token            — JWT ADMIN
  viewer_token           — JWT VIEWER
  auth_headers_operator  — {"Authorization": "Bearer ..."}
  auth_headers_admin
  auth_headers_viewer
"""

import asyncio
import os

# Устанавливаем секрет для подписи JWT, чтобы Settings не падал при инициализации
# Это должно быть сделано ДО импорта каких-либо модулей gateway_service
os.environ["JWT_SECRET"] = "test-secret-key-minimum-32-chars-ok!"

# Патчим bcrypt, чтобы избежать ошибки "password cannot be longer than 72 bytes"
# во время инициализации passlib (это происходит при проверке wraparound bug)
try:
    import bcrypt as bcrypt_lib
    from unittest.mock import patch as mock_patch
    
    # Сохраняем оригинальный hashpw
    original_hashpw = bcrypt_lib.hashpw
    
    def patched_hashpw(password, salt):
        """Патчированный hashpw, который обрезает пароль до 72 байт перед хешированием"""
        if isinstance(password, bytes) and len(password) > 72:
            password = password[:72]
        return original_hashpw(password, salt)
    
    # Применяем патч глобально
    bcrypt_lib.hashpw = patched_hashpw
except Exception as e:
    # Если что-то пошло не так, просто продолжаем
    pass

from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from gateway_service.auth.jwt import create_access_token
from gateway_service.auth.schemas import UserRole
from gateway_service.config import Settings, get_settings


# ─── ID тестовых пользователей ───────────────────────────────────────────────

TEST_USER_OPERATOR_ID = "00000000-0000-0000-0000-000000000001"
TEST_USER_ADMIN_ID    = "00000000-0000-0000-0000-000000000002"
TEST_USER_VIEWER_ID   = "00000000-0000-0000-0000-000000000003"


# ─── Settings ────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Settings для тестовой среды: без реальных соединений."""
    return Settings(  # type: ignore[call-arg]
        environment="development",
        jwt_secret="test-secret-key-minimum-32-chars-ok!",
        jwt_access_expire_minutes=5,
        jwt_refresh_expire_days=1,
        redis_url="redis://localhost:6379/15",
        rabbitmq_url="amqp://guest:guest@localhost:5672/",
        orchestrator_grpc_host="localhost",
        orchestrator_grpc_port=50051,
        metrics_enabled=False,
        tracing_enabled=False,
        log_level="WARNING",
    )


# ─── Mock-сервисы ────────────────────────────────────────────────────────────


@pytest.fixture
def mock_redis() -> MagicMock:
    """Заглушка RedisClient — все методы AsyncMock."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=False)
    redis.hset = AsyncMock(return_value=1)
    redis.hgetall = AsyncMock(return_value={})
    redis.publish = AsyncMock(return_value=1)
    redis.ping = AsyncMock(return_value=True)
    redis.connect = AsyncMock()
    redis.close = AsyncMock()

    # Настройка PubSub мока
    pubsub = MagicMock()
    pubsub.subscribe = AsyncMock()
    pubsub.psubscribe = AsyncMock()
    pubsub.unsubscribe = AsyncMock()
    pubsub.punsubscribe = AsyncMock()
    pubsub.aclose = AsyncMock()
    
    # Чтобы поддерживать `async for message in pubsub.listen()`
    # мы должны сделать listen асинхронным генератором или вернуть объект с __aiter__
    async def mock_listen():
        # Keep the iterator alive until cancelled.
        while True:
            await asyncio.sleep(0.1)
            # Never yield anything by default, or yield a dummy if needed
            if False: yield None
    
    pubsub.listen = mock_listen
    redis.pubsub = MagicMock(return_value=pubsub)
    
    return redis


@pytest.fixture
def mock_rabbitmq() -> MagicMock:
    """Заглушка RabbitMQPublisher."""
    rmq = MagicMock()
    rmq.publish = AsyncMock()
    rmq.publish_command = AsyncMock()
    rmq.publish_event = AsyncMock()
    rmq.is_healthy = AsyncMock(return_value=True)
    rmq.connect = AsyncMock()
    rmq.close = AsyncMock()
    return rmq


@pytest.fixture
def mock_grpc() -> MagicMock:
    """Заглушка OrchestratorGrpcClient."""
    grpc = MagicMock()
    grpc.connect = AsyncMock()
    grpc.close = AsyncMock()
    grpc.is_healthy = AsyncMock(return_value=True)
    grpc.get_robot_state = AsyncMock(return_value={"id": "r1", "name": "Robot 1", "status": "idle", "battery": 95})
    grpc.get_task_status = AsyncMock(return_value={"task_id": "t1", "status": "running", "progress": 50})
    grpc.submit_command = AsyncMock(return_value={"task_id": "new-task", "accepted": True})
    grpc.list_robots = AsyncMock(return_value=[{"id": "r1", "name": "Robot 1"}])
    grpc.list_tasks = AsyncMock(return_value=[])
    grpc.list_zones = AsyncMock(return_value=[])
    grpc.get_zone = AsyncMock(return_value=None)
    return grpc


# ─── Приложение ──────────────────────────────────────────────────────────────


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """
    FastAPI приложение для тестов.
    Переопределяем lifespan на пустой, чтобы избежать попыток подключения к реальным БД/брокерам.
    """
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def mock_lifespan(app: FastAPI):
        yield

    get_settings.cache_clear()
    with patch("gateway_service.main.lifespan", mock_lifespan):
        from gateway_service.main import create_app
        application = create_app()
    
    # Используем FastAPI dependency_overrides для подмены get_settings
    application.dependency_overrides[get_settings] = lambda: test_settings
    return application


@pytest.fixture(autouse=True)
def _inject_mock_services(
    app: FastAPI,
    mock_redis: MagicMock,
    mock_rabbitmq: MagicMock,
    mock_grpc: MagicMock,
) -> None:
    """Подменяет сервисы в app.state перед каждым тестом (autouse)."""
    app.state.redis = mock_redis
    app.state.rabbitmq = mock_rabbitmq
    app.state.grpc_client = mock_grpc


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Async httpx клиент для интеграционных тестов."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


# ─── Токены ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def operator_token(test_settings: Settings) -> str:
    return create_access_token(
        subject=TEST_USER_OPERATOR_ID,
        role=UserRole.OPERATOR,
        settings=test_settings,
    )


@pytest.fixture(scope="session")
def admin_token(test_settings: Settings) -> str:
    return create_access_token(
        subject=TEST_USER_ADMIN_ID,
        role=UserRole.ADMIN,
        settings=test_settings,
    )


@pytest.fixture(scope="session")
def viewer_token(test_settings: Settings) -> str:
    return create_access_token(
        subject=TEST_USER_VIEWER_ID,
        role=UserRole.VIEWER,
        settings=test_settings,
    )


@pytest.fixture(scope="session")
def auth_headers_operator(operator_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {operator_token}"}


@pytest.fixture(scope="session")
def auth_headers_admin(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def auth_headers_viewer(viewer_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {viewer_token}"}


# ─── Очистка in-memory хранилищ ──────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_zone_store() -> None:
    """Очищает _ZoneStore._data перед каждым тестом — изолирует состояние."""
    from gateway_service.api.v1.zones import _ZoneStore
    _ZoneStore._data.clear()


# ─── Синхронный клиент для WebSocket-тестов ──────────────────────────────────


@pytest.fixture
def sync_client(app: FastAPI):
    """Синхронный starlette TestClient для WebSocket тестов."""
    from starlette.testclient import TestClient
    with TestClient(app, raise_server_exceptions=False) as tc:
        yield tc
