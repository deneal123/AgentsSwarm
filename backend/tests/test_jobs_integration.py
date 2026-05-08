import uuid
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from service import container as di
from service.models.auth_models import AuthProfile
from service.models.key_value import ProcessingStatus, ServiceType, UserTypes
from service.presentation.dependencies.auth_checker import check_auth
from service.presentation.routers.jobs_api.jobs_api import jobs_router
from service.presentation.routers.jobs_api.schemas import StartJobRequest
from service.services.chat.domain.chat_contracts import JobExecutionResult


# ---- Fakes for dependency overrides ----
@dataclass
class _Job:
    id: uuid.UUID
    user_id: uuid.UUID
    req: StartJobRequest


class _FakeJobService:
    def __init__(self) -> None:
        self._jobs: dict[uuid.UUID, _Job] = {}
        self.wait_time = 5

    async def create_job(self, user_id: uuid.UUID, request_body: StartJobRequest) -> JobExecutionResult:
        job_id = uuid.uuid4()
        self._jobs[job_id] = _Job(id=job_id, user_id=user_id, req=request_body)
        # For CALENDAR jobs we set longer wait time in real service; mimic minimally
        wait_time = (
            self.wait_time if request_body.type != ServiceType.CALENDAR else max(self.wait_time, 15)
        )
        return JobExecutionResult(
            job_id=job_id,
            status=ProcessingStatus.NEW,
            result_file_url=None,
            wait_time_sec=wait_time,
        )

    async def fetch_job_result(self, user_id: uuid.UUID, job_id: uuid.UUID) -> JobExecutionResult:
        job = self._jobs.get(job_id)
        assert job is not None and job.user_id == user_id
        return JobExecutionResult(
            job_id=job_id,
            status=ProcessingStatus.SUCCESS,
            result_file_url=None,
            wait_time_sec=0,
        )


_TEST_USER_ID = uuid.uuid4()


def _fake_auth() -> AuthProfile:
    # Stable user id across multiple requests in the test
    return AuthProfile(user_id=_TEST_USER_ID, fingerprint=None, type=UserTypes.REGISTERED)


def test_job_flow_train_enrichment():
    app = FastAPI()
    app.include_router(jobs_router)

    # Provide Fake JobService by monkeypatching container.get (route captured lambda at import time)
    fake_service = _FakeJobService()
    _orig_get = di.get

    def _patched_get(name: str):  # noqa: D401
        if name == di.JobServiceName:
            return fake_service
        return _orig_get(name)

    di.get = _patched_get  # type: ignore
    app.dependency_overrides[check_auth] = _fake_auth

    client = TestClient(app)

    body = {
        "file_id": str(uuid.uuid4()),
        "type": ServiceType.CALENDAR.value,
    }

    # Start job
    resp = client.post("/api/jobs/v1/start", json=body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == ProcessingStatus.NEW.value
    job_id = data["job_id"]

    # Fetch result
    resp2 = client.get(f"/api/jobs/v1/result/{job_id}")
    assert resp2.status_code == 200, resp2.text
    data2 = resp2.json()
    assert data2["status"] == ProcessingStatus.SUCCESS.value
