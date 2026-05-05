import pytest
from fastapi.testclient import TestClient
from service.main import app
from service.presentation.routers import jobs_api


def test_get_task_status_custom_state(monkeypatch):
    # Import actual router module to patch its USE_CELERY flag
    import importlib

    mod = importlib.import_module("service.presentation.routers.jobs_api.jobs_api")
    monkeypatch.setattr(mod, "USE_CELERY", True)

    class FakeResult:
        def __init__(self):
            self.state = "CUSTOM"
            self.info = {"progress": 42, "status": "halfway"}
            self.result = None

        def ready(self):
            return False

        def successful(self):
            return False

    # Patch celery.result.AsyncResult to return our fake
    import celery.result

    monkeypatch.setattr(celery.result, "AsyncResult", lambda tid, app=None: FakeResult())

    from service.presentation.dependencies.auth_checker import check_auth
    from service.models.auth_models import AuthProfile
    from service.models.key_value import UserTypes

    client = TestClient(app)
    client.app.dependency_overrides[check_auth] = lambda: AuthProfile(user_id="00000000-0000-0000-0000-000000000000", fingerprint=None, type=UserTypes.REGISTERED)
    resp = client.get("/api/jobs/v1/task/abc/status")
    assert resp.status_code == 200
    j = resp.json()
    assert j["state"] == "CUSTOM"
    assert j["progress"] == 42
    assert j["status"] == "halfway"
