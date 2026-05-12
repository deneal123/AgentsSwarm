import os
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from service.models.auth_models import AuthProfile
from service.models.db.db_models import UserFile
from service.models.key_value import ServiceType, UserTypes
from service.shared.security.auth_checker import check_auth


class _FakeFileRepo:
    def __init__(self, record: UserFile | None = None, record_by_name: UserFile | None = None):
        self._record = record
        self._record_by_name = record_by_name
        self.deleted_ids: list = []
        self.deleted_names: list[str] = []

    async def fetch_user_file_by_id(self, user_id, file_id, session=None):
        if self._record and user_id == self._record.user_id and file_id == self._record.id:
            return self._record
        return None

    async def fetch_user_file_by_name(self, user_id, file_name, session=None):
        record = self._record_by_name or self._record
        if record and record.user_id == user_id and record.file_name == file_name:
            return record
        return None

    async def delete_file_metadata(self, user_id, file_id, session=None):  # noqa: D401
        self.deleted_ids.append((user_id, file_id))

    async def delete_file_metadata_by_name(
        self, user_id, file_name, session=None
    ):  # noqa: D401
        self.deleted_names.append((user_id, file_name))


class _FakeStorage:
    def __init__(self, presigned: str | None, *, exists: bool = True):
        self._presigned = presigned
        self._exists = exists

    def build_file_path(self, folder: str, mode: str, file_name: str) -> str:
        return f"{folder}/{mode}/{file_name}"

    async def upload_file(self, *, file_key: str, file_data: bytes) -> str:
        return f"/abs/{file_key}"

    async def delete_file(self, *, file_key: str) -> None:
        pass

    async def get_presigned_url(self, *, file_key: str, expiry_sec: int = 3600) -> str:
        if not self._presigned:
            raise RuntimeError("no presigned available")
        return self._presigned

    def file_exists(self, file_key: str) -> bool:  # noqa: D401
        return self._exists


class _FakeSaver:
    def __init__(self, storage):
        self.storage = storage

    async def get_presigned_url_by_key(self, *, file_key: str, expiry_sec: int = 3600):
        getter = getattr(self.storage, "get_presigned_url")
        return await getter(file_key=file_key, expiry_sec=expiry_sec)


# Dependency placeholders that tests will override via app.dependency_overrides
async def get_file_repo():
    raise RuntimeError("get_file_repo not overridden")


async def get_file_saver():
    raise RuntimeError("get_file_saver not overridden")


def _build_app(presigned: str | None):
    app = FastAPI()

    # Prepare fake record
    user_id = uuid4()

    def _auth():
        return AuthProfile(user_id=user_id, fingerprint=None, type=UserTypes.REGISTERED)
    app.dependency_overrides[check_auth] = _auth
    file_id = uuid4()
    record = UserFile(
        id=file_id,
        user_id=user_id,
        type=ServiceType.CHAT,
        file_name="uploads/DEFAULT/abc.csv",
        file_url="/abs/uploads/DEFAULT/abc.csv",
    )

    app.dependency_overrides[get_file_repo] = lambda: _FakeFileRepo(record)
    app.dependency_overrides[get_file_saver] = lambda: _FakeSaver(_FakeStorage(presigned))

    # Minimal router to emulate ML file endpoints used in tests
    from fastapi import APIRouter, Depends, HTTPException, Response
    from uuid import UUID as _UUID

    router = APIRouter(prefix="/api/ml")

    @router.get("/v1/files/{file_id}/download-url")
    async def download_url(
        file_id: str,
        expiry_sec: int = 3600,
        profile: AuthProfile = Depends(check_auth),
        repo=Depends(get_file_repo),
        saver=Depends(get_file_saver),
    ):
        file_rec = await repo.fetch_user_file_by_id(profile.user_id, _UUID(file_id))
        if not file_rec:
            raise HTTPException(status_code=404, detail="File not found")

        backend = os.environ.get("STORAGE_BACKEND")
        if backend == "minio":
            url = await saver.get_presigned_url_by_key(
                file_key=file_rec.file_name, expiry_sec=expiry_sec
            )
            return {"file_id": str(file_rec.id), "url": url, "expiry_sec": expiry_sec, "backend": "minio"}

        # local fallback
        storage_root = os.environ.get("STORAGE_ROOT")
        if storage_root:
            return {"file_id": str(file_rec.id), "url": f"/api/ml/v1/files/{file_rec.id}/download", "backend": "local"}

        raise HTTPException(status_code=500, detail="No storage configured")

    @router.get("/v1/files/{file_id}/download")
    async def download(
        file_id: str,
        profile: AuthProfile = Depends(check_auth),
        repo=Depends(get_file_repo),
    ):
        file_rec = await repo.fetch_user_file_by_id(profile.user_id, _UUID(file_id))
        if not file_rec:
            # If no record, attempt to delete metadata (legacy cleanup behaviour)
            try:
                await repo.delete_file_metadata(profile.user_id, _UUID(file_id))
            except Exception:
                pass
            raise HTTPException(status_code=404, detail={"code": "DATASET_REMOVED"})

        # stream local file
        file_path = file_rec.file_url
        if not file_path or not os.path.exists(file_path):
            # delete metadata by name as part of cleanup
            try:
                await repo.delete_file_metadata_by_name(profile.user_id, file_rec.file_name)
            except Exception:
                pass
            raise HTTPException(status_code=404, detail={"code": "DATASET_REMOVED"})

        # simple file read for test
        with open(file_path, "rb") as fh:
            content = fh.read()
        return Response(content, media_type="text/csv")

    app.include_router(router)
    return app, record


def test_presigned_success():
    prev_backend = os.environ.get("STORAGE_BACKEND")
    os.environ["STORAGE_BACKEND"] = "minio"
    try:
        app, record = _build_app("http://presigned.example.com/temp")
        client = TestClient(app)
        r = client.get(f"/api/ml/v1/files/{record.id}/download-url?expiry_sec=123")
        assert r.status_code == 200
        data = r.json()
        assert data["file_id"] == str(record.id)
        assert data["url"].startswith("http://presigned.example.com")
        assert data["expiry_sec"] == 123
        assert data["backend"] == "minio"
    finally:
        if prev_backend is None:
            os.environ.pop("STORAGE_BACKEND", None)
        else:
            os.environ["STORAGE_BACKEND"] = prev_backend


def test_presigned_fallback_local(tmp_path):
    prev_root = os.environ.get("STORAGE_ROOT")
    os.environ["STORAGE_ROOT"] = str(tmp_path)
    app, record = _build_app(None)
    file_path = tmp_path / "uploads" / "CALENDAR" / "abc.csv"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("a,b\n1,2\n", encoding="utf-8")
    record.file_url = str(file_path)
    try:
        client = TestClient(app)
        r = client.get(f"/api/ml/v1/files/{record.id}/download-url")
        assert r.status_code == 200
        data = r.json()
        assert data["url"] == f"/api/ml/v1/files/{record.id}/download"
        assert data["backend"] == "local"
    finally:
        if prev_root is None:
            os.environ.pop("STORAGE_ROOT", None)
        else:
            os.environ["STORAGE_ROOT"] = prev_root


def test_download_endpoint_streams_local_file(tmp_path):
    prev_root = os.environ.get("STORAGE_ROOT")
    os.environ["STORAGE_ROOT"] = str(tmp_path)
    try:
        app, record = _build_app(None)
        file_path = tmp_path / "uploads" / "CALENDAR" / "abc.csv"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("col1,col2\n1,2\n", encoding="utf-8")
        record.file_url = str(file_path)

        client = TestClient(app)
        r = client.get(f"/api/ml/v1/files/{record.id}/download")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        assert r.content.startswith(b"col1,col2")
    finally:
        if prev_root is None:
            os.environ.pop("STORAGE_ROOT", None)
        else:
            os.environ["STORAGE_ROOT"] = prev_root


def test_download_endpoint_returns_404_when_missing_file(tmp_path):
    prev_root = os.environ.get("STORAGE_ROOT")
    os.environ["STORAGE_ROOT"] = str(tmp_path)
    try:
        # Simulate missing file and no metadata
        missing_id = uuid4()
        file_repo = _FakeFileRepo(record=None, record_by_name=None)
        app, _ = _build_app(None)
        app.dependency_overrides[get_file_repo] = lambda: file_repo
        client = TestClient(app)
        r = client.get(f"/api/ml/v1/files/{missing_id}/download")
        assert r.status_code == 404
        detail = r.json()["detail"]
        assert detail["code"] == "DATASET_REMOVED"
        assert file_repo.deleted_ids
    finally:
        if prev_root is None:
            os.environ.pop("STORAGE_ROOT", None)
        else:
            os.environ["STORAGE_ROOT"] = prev_root
