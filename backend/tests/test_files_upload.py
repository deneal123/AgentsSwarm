import io
import pytest
from fastapi.testclient import TestClient

from service.main import app
from service.composition.state import get_file_saver_service
from service.shared.security.auth_checker import check_auth
from service.models.auth_models import AuthProfile
from service.models.key_value import UserTypes


def _fake_auth():
    return AuthProfile(user_id="00000000-0000-0000-0000-000000000000", fingerprint=None, type=UserTypes.REGISTERED)


def test_upload_accepts_uppercase_extension():
    class FakeSaver:
        async def save(self, user_id, mode, file_name, file_content):
            from service.services.files.application.dto import UploadResponse
            return UploadResponse(file_id="00000000-0000-0000-0000-000000000000", file_url="/abs/path", file_key=file_name)

    app.dependency_overrides[check_auth] = lambda: _fake_auth()
    app.dependency_overrides[get_file_saver_service] = lambda: FakeSaver()

    try:
        client = TestClient(app)
        files = {"file": ("test.PNG", io.BytesIO(b"PNGDATA"), "image/png")}
        resp = client.post("/api/service/files/v1/upload/CHAT", files=files)
        assert resp.status_code not in (400,) or "extension" not in resp.text
    finally:
        app.dependency_overrides.pop(check_auth, None)
        app.dependency_overrides.pop(get_file_saver_service, None)


def test_upload_rejects_large_file():
    class FakeSaver:
        async def save(self, user_id, mode, file_name, file_content):
            from service.services.files.application.dto import UploadResponse
            return UploadResponse(file_id="id", file_url="/abs/", file_key=file_name)

    app.dependency_overrides[check_auth] = lambda: _fake_auth()
    app.dependency_overrides[get_file_saver_service] = lambda: FakeSaver()

    try:
        client = TestClient(app)
        big = b"x" * (2_000_001)
        files = {"file": ("big.png", io.BytesIO(big), "image/png")}
        resp = client.post("/api/service/files/v1/upload/CHAT", files=files)
        assert resp.status_code == 400
        assert "File too large" in resp.text
    finally:
        app.dependency_overrides.pop(check_auth, None)
        app.dependency_overrides.pop(get_file_saver_service, None)
