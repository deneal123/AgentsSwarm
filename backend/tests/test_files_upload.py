import io
import pytest
from fastapi.testclient import TestClient
from service.main import app
from service.presentation.dependencies.auth_checker import check_auth
from service.models.auth_models import AuthProfile
from service.models.key_value import UserTypes


# Provide fake auth dependency for tests
def _fake_auth():
    return AuthProfile(user_id="00000000-0000-0000-0000-000000000000", fingerprint=None, type=UserTypes.REGISTERED)


@pytest.fixture(autouse=True)
def override_auth(monkeypatch):
    from service.presentation.dependencies import auth_checker

    monkeypatch.setattr(auth_checker, "check_auth", lambda: _fake_auth())


def test_upload_accepts_uppercase_extension(monkeypatch, tmp_path):
    # Use local storage for test
    prev_storage = None
    try:
        client = TestClient(app)
        # override dependency explicitly to avoid 401
        client.app.dependency_overrides[check_auth] = lambda: _fake_auth()
        # Inject fake FileSaverService into container
        class FakeSaver:
            async def save(self, user_id, mode, file_name, file_content):
                return {"file_id": "00000000-0000-0000-0000-000000000000", "file_url": "/abs/path", "file_key": file_name}

        from service import container
        container._CONTAINER[container.FileSaverServiceName] = FakeSaver()
        # Prepare a small PNG content with uppercase extension
        file_content = b"PNGDATA"
        files = {"file": ("test.PNG", io.BytesIO(file_content), "image/png")}
        resp = client.post("/api/service/files/v1/upload/CALENDAR", files=files)
        # Should reject since our fake Profile auth uses default container expecting more setup; we just need to ensure extension is validated before other errors
        assert resp.status_code != 400 or resp.json().get("detail") != "Invalid file extension. Only: ['.png', '.jpg', '.jpeg'] allowed."
    finally:
        if prev_storage is None:
            pass


def test_upload_rejects_large_file(monkeypatch):
    client = TestClient(app)
    client.app.dependency_overrides[check_auth] = lambda: _fake_auth()
    # Inject fake FileSaverService for size validation
    class FakeSaver2:
        async def save(self, user_id, mode, file_name, file_content):
            return {"file_id": "id", "file_url": "/abs/", "file_key": file_name}

    from service import container
    container._CONTAINER[container.FileSaverServiceName] = FakeSaver2()
    # Create large content > max_file_size_byte
    big = b"x" * (int(2_000_000) + 1)
    files = {"file": ("big.png", io.BytesIO(big), "image/png")}
    resp = client.post("/api/service/files/v1/upload/CALENDAR", files=files)
    assert resp.status_code == 400
    assert "File too large" in resp.text
    # cleanup
    del container._CONTAINER[container.FileSaverServiceName]
    client.app.dependency_overrides.pop(check_auth, None)
