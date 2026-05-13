import uuid
from dataclasses import dataclass

from fastapi.testclient import TestClient

from service.composition.state import get_job_service
from service.main import app
from service.models.auth_models import AuthProfile
from service.models.key_value import ProcessingStatus, ServiceType, UserTypes
from service.services.chat.domain.chat_contracts import JobExecutionResult
from service.services.jobs.application.dto import StartJobRequest
from service.shared.security.auth_checker import check_auth


@dataclass
class _Job:
    id: uuid.UUID
    user_id: uuid.UUID
    req: StartJobRequest


class _FakeJobService:
    def __init__(self) -> None:
        self._jobs: dict[uuid.UUID, _Job] = {}
        self.wait_time = 5

    async def create_job(
        self, user_id: uuid.UUID, request_body: StartJobRequest
    ) -> JobExecutionResult:
        job_id = uuid.uuid4()
        self._jobs[job_id] = _Job(id=job_id, user_id=user_id, req=request_body)
        wait_time = self.wait_time
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
    return AuthProfile(user_id=_TEST_USER_ID, fingerprint=None, type=UserTypes.REGISTERED)


def test_job_flow_train_enrichment():
    fake_service = _FakeJobService()

    app.dependency_overrides[check_auth] = _fake_auth
    app.dependency_overrides[get_job_service] = lambda: fake_service

    try:
        client = TestClient(app)

        body = {"file_id": str(uuid.uuid4()), "type": ServiceType.CHAT.value}

        resp = client.post("/api/jobs/v1/start", json=body)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == ProcessingStatus.NEW.value
        job_id = data["job_id"]

        resp2 = client.get(f"/api/jobs/v1/result/{job_id}")
        assert resp2.status_code == 200, resp2.text
        assert resp2.json()["status"] == ProcessingStatus.SUCCESS.value
    finally:
        app.dependency_overrides.pop(check_auth, None)
        app.dependency_overrides.pop(get_job_service, None)
