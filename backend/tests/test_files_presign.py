from uuid import UUID

from fastapi.testclient import TestClient

from service.composition.state import get_file_saver_service
from service.main import app
from service.models.auth_models import AuthProfile
from service.models.key_value import UserTypes
from service.shared.security.auth_checker import check_auth


def _fake_auth():
    return AuthProfile(
        user_id="00000000-0000-0000-0000-000000000000", fingerprint=None, type=UserTypes.REGISTERED
    )


class FakeSaver:
    async def presign_upload(self, user_id, mode, file_name, expiry_sec=None):
        return {
            "file_id": "00000000-0000-0000-0000-000000000000",
            "file_key": "folder/CHAT/test.jpg",
            "upload_url": "https://upload.local/test",
        }

    async def finalize_upload(self, user_id, mode, file_id, file_key):
        return {"file_id": file_id, "file_url": f"s3://bucket/{file_key}"}

    async def fetch_file_metadata(self, user_id, file_id):
        from service.models.file_models import FileMetadataLogic

        return FileMetadataLogic(
            file_id=file_id if isinstance(file_id, UUID) else UUID(str(file_id)),
            file_url="s3://bucket/folder/TRAINING/test.jpg",
        )

    async def get_presigned_url_by_key(self, *, file_key, expiry_sec=3600):
        return f"https://download.local/{file_key}"


def test_presign_and_callback():
    app.dependency_overrides[check_auth] = lambda: _fake_auth()
    app.dependency_overrides[get_file_saver_service] = lambda: FakeSaver()

    try:
        client = TestClient(app)

        resp = client.post("/api/service/files/v1/presign/CHAT", json={"filename": "test.jpg"})
        assert resp.status_code == 200
        assert resp.json()["upload_url"].startswith("https://")

        resp2 = client.post(
            "/api/service/files/v1/00000000-0000-0000-0000-000000000000/callback",
            json={"file_key": "folder/CHAT/test.jpg", "mode": "CHAT"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["file_url"].startswith("s3://")

        resp3 = client.get("/api/service/files/v1/00000000-0000-0000-0000-000000000000")
        assert resp3.status_code == 200
        assert "download_url" in resp3.json()
    finally:
        app.dependency_overrides.pop(check_auth, None)
        app.dependency_overrides.pop(get_file_saver_service, None)
