from fastapi.testclient import TestClient
from service.main import app
from service import container
from service.settings import config
from service.models.profile_models import UserProfileLogic
from datetime import datetime, timezone
import uuid


class FakeProfileService:
    def __init__(self):
        now = datetime.now(timezone.utc)
        self.user = UserProfileLogic(
            id=uuid.uuid4(),
            email="user@example.com",
            password_hash="hash",
            first_name="A",
            company="C",
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


def test_login_sets_cookie(monkeypatch):
    fake_profile_service = FakeProfileService()
    class FakeAuthService:
        def __init__(self, profile_service):
            self.profile_source = profile_service

        async def login(self, user_agent, request_body):
            # emulate login: create jwt and return LoginResponse-like object
            class R:
                pass

            r = R()
            r.jwt = "token-123"
            r.available_attempts = 3
            return r

    fake_auth = FakeAuthService(fake_profile_service)
    # inject fake services into container
    container._CONTAINER[container.AuthServiceName] = fake_auth
    container._CONTAINER[container.ProfileServiceName] = fake_profile_service

    client = TestClient(app)
    resp = client.post("/api/auth/v1/login", json={"email": "user@example.com", "password": "pass"})
    assert resp.status_code == 200
    # ensure cookie present
    cookies = resp.cookies
    assert "auth_token" in cookies
    # cookie max-age equals config.auth.jwt_exp_hours * 3600
    ck = resp.headers.get("set-cookie")
    assert f"Max-Age={int(config.auth.jwt_exp_hours * 3600)}" in ck

    # cleanup
    del container._CONTAINER[container.ProfileServiceName]
    del container._CONTAINER[container.AuthServiceName]
