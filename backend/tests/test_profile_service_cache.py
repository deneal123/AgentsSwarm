import uuid
from datetime import datetime, timezone

import pytest

from service.models.profile_models import UserProfileLogic
from service.services.profile.application.profile_service import ProfileService
from service.settings import ProfileConfig


class InMemoryCache:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], dict] = {}

    async def set_json(self, namespace: str, key: str, payload: dict, ttl_seconds: int | None = None) -> None:
        self.store[(namespace, key)] = dict(payload)

    async def get_json(self, namespace: str, key: str) -> dict | None:
        item = self.store.get((namespace, key))
        return dict(item) if item is not None else None

    async def invalidate(self, namespace: str, key: str) -> None:
        self.store.pop((namespace, key), None)


class FakeProfileRepository:
    def __init__(self, initial_users: list[UserProfileLogic] | None = None) -> None:
        self._users: dict[str, UserProfileLogic] = {}
        self.fetch_by_id_calls = 0
        self.fetch_by_email_calls = 0
        self.create_calls = 0
        self.update_calls = 0

        if initial_users:
            for user in initial_users:
                self._users[str(user.id)] = user

    async def create_user(self, email: str, password_hash: str, base_available_launches: int = 10, session=None) -> UserProfileLogic:
        self.create_calls += 1
        now = datetime.now(timezone.utc)
        user = UserProfileLogic(
            id=uuid.uuid4(),
            email=email,
            password_hash=password_hash,
            first_name=None,
            timezone=None,
            avatar_url=None,
            created_at=now,
            updated_at=now,
        )
        self._users[str(user.id)] = user
        return user

    async def fetch_user_profile(self, user_id, session=None) -> UserProfileLogic | None:
        self.fetch_by_id_calls += 1
        return self._users.get(str(user_id))

    async def fetch_user_by_email(self, email: str, session=None) -> UserProfileLogic | None:
        self.fetch_by_email_calls += 1
        for user in self._users.values():
            if user.email.lower() == email.lower():
                return user
        return None

    async def update_user_profile(self, user: UserProfileLogic, session=None) -> UserProfileLogic:
        self.update_calls += 1
        self._users[str(user.id)] = user
        return user


@pytest.fixture()
def profile_conf() -> ProfileConfig:
    return ProfileConfig(base_available_launches=3)


def _make_user() -> UserProfileLogic:
    now = datetime.now(timezone.utc)
    return UserProfileLogic(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash="hash",
        first_name="Test",
        timezone=None,
        avatar_url=None,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_fetch_user_profile_uses_cache(profile_conf: ProfileConfig) -> None:
    user = _make_user()
    repo = FakeProfileRepository([user])
    cache = InMemoryCache()
    service = ProfileService(profile_conf, repo, cache=cache, cache_ttl_seconds=60)

    result_first = await service.fetch_user_profile(user.id)
    assert result_first.id == user.id
    assert repo.fetch_by_id_calls == 1

    result_second = await service.fetch_user_profile(user.id)
    assert repo.fetch_by_id_calls == 1, "Expected cache hit on second fetch"
    assert result_second.email == user.email


@pytest.mark.asyncio
async def test_create_new_user_populates_cache(profile_conf: ProfileConfig) -> None:
    repo = FakeProfileRepository()
    cache = InMemoryCache()
    service = ProfileService(profile_conf, repo, cache=cache, cache_ttl_seconds=120)

    created = await service.create_new_user("new.user@example.com", "Password1234")
    assert repo.create_calls == 1

    repo.fetch_by_email_calls = 0
    cached = await service.fetch_user_profile_by_email("new.user@example.com")
    assert cached is not None and cached.id == created.id
    assert repo.fetch_by_email_calls == 0


@pytest.mark.asyncio
async def test_update_count_attempts_refreshes_cache(profile_conf: ProfileConfig) -> None:
    user = _make_user()
    repo = FakeProfileRepository([user])
    cache = InMemoryCache()
    service = ProfileService(profile_conf, repo, cache=cache, cache_ttl_seconds=30)

    await service.fetch_user_profile(user.id)
    assert repo.fetch_by_id_calls == 1

    updated_user = user.model_copy(update={"first_name": "Updated"})
    repo._users[str(user.id)] = updated_user
    cache.store.clear()

    repo.fetch_by_id_calls = 0
    result = await service.fetch_user_profile(user.id)
    assert result.first_name == "Updated"
    assert repo.fetch_by_id_calls == 1
