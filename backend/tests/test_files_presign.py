import json
from uuid import UUID

from fastapi.testclient import TestClient
from service.main import app
from service.presentation.dependencies.auth_checker import check_auth
from service.models.auth_models import AuthProfile
from service.models.key_value import ServiceType, UserTypes


def _fake_auth():
    return AuthProfile(user_id="00000000-0000-0000-0000-000000000000", fingerprint=None, type=UserTypes.REGISTERED)


def test_presign_and_callback(monkeypatch):
    client = TestClient(app)
    client.app.dependency_overrides[check_auth] = lambda: _fake_auth()

    class FakeSaver:
        async def presign_upload(self, user_id, mode, file_name, expiry_sec=None):
            return {"file_id": "00000000-0000-0000-0000-000000000000", "file_key": "folder/CALENDAR/test.jpg", "upload_url": "https://upload.local/test"}

        async def finalize_upload(self, user_id, mode, file_id, file_key):
            return {"file_id": file_id, "file_url": f"s3://bucket/{file_key}"}

        async def fetch_file_metadata(self, user_id, file_id):
            class Meta: pass
            m = Meta()
            m.file_id = file_id if isinstance(file_id, UUID) else UUID(file_id)
            m.file_url = f"s3://bucket/folder/TRAINING/test.jpg"
            return m

        async def get_presigned_url_by_key(self, file_key, expiry_sec=3600):
            return f"https://download.local/{file_key}"

    from service import container

    container._CONTAINER[container.FileSaverServiceName] = FakeSaver()

    # Presign
    resp = client.post("/api/service/files/v1/presign/CALENDAR", json={"filename": "test.jpg"})
    assert resp.status_code == 200
    j = resp.json()
    assert j["upload_url"].startswith("https://")

    # Callback
    resp2 = client.post("/api/service/files/v1/00000000-0000-0000-0000-000000000000/callback", json={"file_key": "folder/CALENDAR/test.jpg", "mode": "CALENDAR"})
    assert resp2.status_code == 200
    j2 = resp2.json()
    assert j2["file_url"].startswith("s3://")

    # Get file metadata
    resp3 = client.get("/api/service/files/v1/00000000-0000-0000-0000-000000000000")
    assert resp3.status_code == 200
    j3 = resp3.json()
    assert "download_url" in j3
