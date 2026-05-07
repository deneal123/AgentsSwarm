import uuid
from datetime import datetime, timezone

import pytest

from service.models.profile_models import UserProfileLogic
from service.profile.application.profile_service import ProfileService
from service.settings import ProfileConfig


class InMemoryCache:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], dict] = {}

    async def set_json(
        self, namespace: str, key: str, payload: dict, ttl_seconds: int | None = None
    ) -> None:
        # store payload copy to avoid accidental mutations
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
                self._store_user(user)

    def _store_user(self, user: UserProfileLogic) -> None:
        self._users[str(user.id)] = user

    async def create_user(
        self,
        email: str,
        password_hash: str,
        base_available_launches: int,
        session=None,
    ) -> UserProfileLogic:
        self.create_calls += 1
        now = datetime.now(timezone.utc)
        user = UserProfileLogic(
            id=uuid.uuid4(),
            email=email,
            password_hash=password_hash,
            phone=None,
            first_name=None,
            company=None,
            timezone=None,
            avatar_url=None,
            available_launches=base_available_launches,
            created_at=now,
            updated_at=now,
        )
        self._store_user(user)
        return user

    async def fetch_user_profile(self, user_id: str, session=None) -> UserProfileLogic | None:
        self.fetch_by_id_calls += 1
        return self._users.get(str(user_id))

    async def fetch_user_by_email(self, email: str, session=None) -> UserProfileLogic | None:
        self.fetch_by_email_calls += 1
        email_lower = email.lower()
        for user in self._users.values():
            if user.email.lower() == email_lower:
                return user
        return None

    async def update_user_profile(
        self, user: UserProfileLogic, session=None
    ) -> UserProfileLogic:
        self.update_calls += 1
        self._store_user(user)
        return user


@pytest.fixture()
def profile_conf() -> ProfileConfig:
    return ProfileConfig(base_available_launches=3)


def _make_user(available_launches: int = 5) -> UserProfileLogic:
    now = datetime.now(timezone.utc)
    return UserProfileLogic(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash="hash",
        first_name="Test",
        company=None,
        timezone=None,
        avatar_url=None,
        available_launches=available_launches,
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
    assert result_second.available_launches == user.available_launches


@pytest.mark.asyncio
async def test_create_new_user_populates_cache(profile_conf: ProfileConfig) -> None:
    repo = FakeProfileRepository()
    cache = InMemoryCache()
    service = ProfileService(profile_conf, repo, cache=cache, cache_ttl_seconds=120)

    created = await service.create_new_user("new.user@example.com", "Password1234")
    assert repo.create_calls == 1

    # Cache should allow immediate lookup without repository hit
    repo.fetch_by_email_calls = 0
    cached = await service.fetch_user_profile_by_email("new.user@example.com")
    assert cached is not None and cached.id == created.id
    assert repo.fetch_by_email_calls == 0


@pytest.mark.asyncio
async def test_update_count_attempts_refreshes_cache(profile_conf: ProfileConfig) -> None:
    user = _make_user(available_launches=2)
    repo = FakeProfileRepository([user])
    cache = InMemoryCache()
    service = ProfileService(profile_conf, repo, cache=cache, cache_ttl_seconds=30)

    # Prime cache
    await service.fetch_user_profile(user.id)
    assert repo.fetch_by_id_calls == 1

    updated = await service.update_count_attempts(user.id, 7)
    assert repo.update_calls == 1
    assert updated.available_launches == 7

    # Subsequent fetch should use refreshed cache without additional repo calls
    repo.fetch_by_id_calls = 0
    cached = await service.fetch_user_profile(user.id)
    assert repo.fetch_by_id_calls == 0
    assert cached.available_launches == 7
