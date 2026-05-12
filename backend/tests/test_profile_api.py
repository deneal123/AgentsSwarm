import uuid
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from service.models.auth_models import AuthProfile
from service.models.key_value import UserTypes
from service.services.profile.application.dto import ProfileOverviewResult
from service.services.profile.presentation.routers.profile_api import profile_api as profile_module
from service.services.profile.presentation.routers.profile_api.profile_api import (
    get_profile_service,
    profile_router,
)


def _fake_auth() -> AuthProfile:
    return AuthProfile(user_id=uuid.uuid4(), fingerprint=None, type=UserTypes.REGISTERED)


class _FakeProfileService:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self._uid = uuid.uuid4()
        self.overview = ProfileOverviewResult(
            id=self._uid,
            email="user@example.com",
            first_name="Alex",
            timezone="Europe/Moscow",
            avatar_url=None,
            created_at=now,
            updated_at=now,
        )
        self.update_calls: list = []
        self.deleted_chat_history_calls: list = []

    async def get_profile_overview(self, query):
        return self.overview

    async def update_profile_details(self, command):
        self.update_calls.append(command)
        if command.first_name is not None:
            self.overview = self.overview.model_copy(update={"first_name": command.first_name})
        if command.timezone is not None:
            self.overview = self.overview.model_copy(update={"timezone": command.timezone})
        return self.overview

    async def delete_chat_history(self, command):
        self.deleted_chat_history_calls.append(command.user_id)


def _make_app(fake_service: _FakeProfileService) -> TestClient:
    app = FastAPI()
    app.include_router(profile_router)

    app.dependency_overrides[get_profile_service] = lambda: fake_service
    app.dependency_overrides[profile_module.check_auth] = _fake_auth

    return TestClient(app)


def test_get_profile_returns_overview():
    fake_service = _FakeProfileService()
    client = _make_app(fake_service)

    resp = client.get("/api/profile/me")

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["email"] == "user@example.com"
    assert payload["first_name"] == "Alex"


def test_patch_profile_updates_fields():
    fake_service = _FakeProfileService()
    client = _make_app(fake_service)

    new_payload = {"first_name": "Nika", "timezone": "Europe/Berlin"}
    resp = client.patch("/api/profile/me", json=new_payload)

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["first_name"] == "Nika"
    assert payload["timezone"] == "Europe/Berlin"

    assert len(fake_service.update_calls) == 1
    cmd = fake_service.update_calls[0]
    assert cmd.first_name == "Nika"
    assert cmd.timezone == "Europe/Berlin"


def test_delete_chat_history_returns_204():
    fake_service = _FakeProfileService()
    client = _make_app(fake_service)

    resp = client.delete("/api/profile/me/chat-history")

    assert resp.status_code == 204, resp.text
    assert len(fake_service.deleted_chat_history_calls) == 1
