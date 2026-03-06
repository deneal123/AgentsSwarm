"""
UserService — абстракция над хранилищем пользователей.

Архитектурно: Gateway не обращается к PostgreSQL напрямую.
Пользователи хранятся в Orchestrator (SQLAlchemy + asyncpg).
Когда gRPC-клиент Orchestrator будет реализован — UserService
переключится на gRPC. До тех пор — используется InMemoryUserService.

Паттерн: Protocol + конкретные реализации.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import structlog
from passlib.context import CryptContext

logger = structlog.get_logger(__name__)

# ─── Password hashing ────────────────────────────────────────────────────────

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ─── Domain model ─────────────────────────────────────────────────────────────

@dataclass
class UserRecord:
    """Запись пользователя (внутреннее представление)."""

    user_id: str
    username: str
    email: str
    hashed_password: str
    role: str
    display_name: str | None = None
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "display_name": self.display_name,
            "is_active": self.is_active,
        }


# ─── Abstract Protocol ───────────────────────────────────────────────────────

class AbstractUserService(ABC):
    """Интерфейс сервиса пользователей."""

    @abstractmethod
    async def authenticate(self, username: str, password: str) -> UserRecord | None:
        """Проверить учётные данные. None — если неверные."""

    @abstractmethod
    async def get_by_id(self, user_id: str) -> UserRecord | None:
        """Найти пользователя по ID."""

    @abstractmethod
    async def get_by_username(self, username: str) -> UserRecord | None:
        """Найти по имени (или email если содержит @)."""

    @abstractmethod
    async def create(
        self,
        username: str,
        email: str,
        password: str,
        role: str,
    ) -> UserRecord:
        """Создать нового пользователя. Raises UserAlreadyExistsError."""

    @abstractmethod
    async def update(
        self,
        user_id: str,
        *,
        email: str | None = None,
        password: str | None = None,
        display_name: str | None = None,
    ) -> UserRecord:
        """Обновить данные пользователя. Raises UserNotFoundError."""


# ─── In-Memory реализация (dev / тесты) ──────────────────────────────────────

class InMemoryUserService(AbstractUserService):
    """
    Хранилище пользователей в памяти.

    Используется в dev-режиме и тестах.
    В production заменяется на GrpcUserService.

    При инициализации создаёт стандартного администратора:
      username: admin, password: Admin123
    """

    def __init__(self) -> None:
        self._users: dict[str, UserRecord] = {}       # user_id → UserRecord
        self._by_username: dict[str, str] = {}        # username → user_id
        self._by_email: dict[str, str] = {}           # email → user_id
        self._initialized = False

    async def _ensure_default_admin(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        admin = UserRecord(
            user_id=str(uuid.uuid4()),
            username="admin",
            email="admin@agentsswarm.io",
            hashed_password=hash_password("Admin123"),
            role="admin",
            display_name="System Administrator",
        )
        self._store(admin)
        logger.info("user_service.default_admin_created", username="admin")

    def _store(self, user: UserRecord) -> None:
        self._users[user.user_id] = user
        self._by_username[user.username.lower()] = user.user_id
        self._by_email[user.email.lower()] = user.user_id

    async def authenticate(self, username: str, password: str) -> UserRecord | None:
        await self._ensure_default_admin()
        user = await self.get_by_username(username)
        if user is None:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def get_by_id(self, user_id: str) -> UserRecord | None:
        await self._ensure_default_admin()
        return self._users.get(user_id)

    async def get_by_username(self, username: str) -> UserRecord | None:
        await self._ensure_default_admin()
        key = username.lower()
        # Поиск по username или email
        user_id = self._by_username.get(key) or self._by_email.get(key)
        if user_id is None:
            return None
        return self._users.get(user_id)

    async def create(
        self,
        username: str,
        email: str,
        password: str,
        role: str,
    ) -> UserRecord:
        from gateway_service.auth.exceptions import UserAlreadyExistsError

        await self._ensure_default_admin()

        if username.lower() in self._by_username:
            raise UserAlreadyExistsError("username")
        if email.lower() in self._by_email:
            raise UserAlreadyExistsError("email")

        user = UserRecord(
            user_id=str(uuid.uuid4()),
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role=role,
        )
        self._store(user)
        logger.info("user_service.created", username=username, role=role)
        return user

    async def update(
        self,
        user_id: str,
        *,
        email: str | None = None,
        password: str | None = None,
        display_name: str | None = None,
    ) -> UserRecord:
        from gateway_service.auth.exceptions import UserNotFoundError

        user = self._users.get(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        if email is not None:
            # Проверяем уникальность нового email
            existing_id = self._by_email.get(email.lower())
            if existing_id and existing_id != user_id:
                from gateway_service.auth.exceptions import UserAlreadyExistsError
                raise UserAlreadyExistsError("email")
            # Удаляем старый email из индекса
            del self._by_email[user.email.lower()]
            user.email = email
            self._by_email[email.lower()] = user_id

        if password is not None:
            user.hashed_password = hash_password(password)

        if display_name is not None:
            user.display_name = display_name

        return user


# ─── Singleton factory ───────────────────────────────────────────────────────

_user_service_instance: AbstractUserService | None = None


def get_user_service() -> AbstractUserService:
    """
    FastAPI Dependency / фабрика.

    В dev/test возвращает InMemoryUserService.
    В production — переопределяется на GrpcUserService при инициализации app.
    """
    global _user_service_instance
    if _user_service_instance is None:
        _user_service_instance = InMemoryUserService()
    return _user_service_instance


def set_user_service(service: AbstractUserService) -> None:
    """Переопределить реализацию (например, при старте app для подключения gRPC)."""
    global _user_service_instance
    _user_service_instance = service
