import pytest
from fastapi.testclient import TestClient
from service.main import app
from service.services.jobs.presentation.routers.jobs_api.jobs_api import get_job_application_service
from service.services.jobs.application.dto import TaskStatusResponse


def test_get_task_status_custom_state():
    class _FakeAppService:
        async def get_task_status(self, task_id: str) -> TaskStatusResponse:
            return TaskStatusResponse(
                task_id=task_id,
                state="CUSTOM",
                progress=42,
                status="halfway",
                result=None,
                error=None,
            )

    from service.shared.security.auth_checker import check_auth
    from service.models.auth_models import AuthProfile
    from service.models.key_value import UserTypes

    app.dependency_overrides[get_job_application_service] = lambda: _FakeAppService()
    app.dependency_overrides[check_auth] = lambda: AuthProfile(
        user_id="00000000-0000-0000-0000-000000000000",
        fingerprint=None,
        type=UserTypes.REGISTERED,
    )
    try:
        client = TestClient(app)
        resp = client.get("/api/jobs/v1/task/abc/status")
        assert resp.status_code == 200
        j = resp.json()
        assert j["state"] == "CUSTOM"
        assert j["progress"] == 42
        assert j["status"] == "halfway"
    finally:
        app.dependency_overrides.pop(get_job_application_service, None)
        app.dependency_overrides.pop(check_auth, None)
