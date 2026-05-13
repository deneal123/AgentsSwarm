import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from service.composition.state import get_auth_service, get_profile_service
from service.main import app
from service.models.profile_models import UserProfileLogic
from service.settings import config


class FakeProfileService:
    def __init__(self):
        now = datetime.now(UTC)
        self.user = UserProfileLogic(
            id=uuid.uuid4(),
            email="user@example.com",
            password_hash="hash",
            first_name="A",
            timezone="UTC",
            avatar_url=None,
            available_launches=3,
            created_at=now,
            updated_at=now,
        )

    async def fetch_user_profile_by_email(self, email):
        return self.user

    def verify_password(self, password, password_hash):
        return True


def test_login_sets_cookie():
    fake_profile_service = FakeProfileService()

    class FakeAuthService:
        async def login(self, user_agent, request_body):
            class R:
                jwt = "token-123"
                available_attempts = 3

            return R()

    client = TestClient(app)
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_profile_service] = lambda: fake_profile_service

    try:
        resp = client.post(
            "/api/auth/v1/login", json={"email": "user@example.com", "password": "pass"}
        )
        assert resp.status_code == 200
        assert "auth_token" in resp.cookies
        ck = resp.headers.get("set-cookie")
        assert f"Max-Age={int(config.auth.jwt_exp_hours * 3600)}" in ck
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
        app.dependency_overrides.pop(get_profile_service, None)
