import uuid
from types import SimpleNamespace

import pytest

from service.models.key_value import ProcessingStatus
from service.repositories.exceptions import RepositoryIntegrityError
from service.services.jobs.application.job_service import ANON_USER_UUID, JobService
from service.settings import JobConfig, config


class _FakeJobRepository:
    def __init__(self, *, fail_user_ids: set[uuid.UUID] | None = None) -> None:
        self.fail_user_ids = fail_user_ids or set()
        self.seen_user_ids: list[uuid.UUID] = []

    async def create_job(self, new_job):  # noqa: ANN001
        self.seen_user_ids.append(new_job.user_id)
        if new_job.user_id in self.fail_user_ids:
            raise RepositoryIntegrityError("fk violation")
        return SimpleNamespace(id=uuid.uuid4(), status=ProcessingStatus.NEW)


@pytest.mark.asyncio
async def test_create_chat_job_prefers_admin_for_anonymous_user(monkeypatch: pytest.MonkeyPatch) -> None:
    admin_uuid = uuid.uuid4()
    monkeypatch.setattr(config.service, "admin_user_ids", [str(admin_uuid)])

    repo = _FakeJobRepository(fail_user_ids={ANON_USER_UUID})
    service = JobService(JobConfig(), repo, profile_source=None)

    await service.create_chat_job(user_id=None, thread_id="thread-1", text="hello")

    assert repo.seen_user_ids[0] == admin_uuid
    assert ANON_USER_UUID not in repo.seen_user_ids


@pytest.mark.asyncio
async def test_create_chat_job_fallbacks_to_admin_when_primary_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    user_uuid = uuid.uuid4()
    admin_uuid = uuid.uuid4()
    monkeypatch.setattr(config.service, "admin_user_ids", [str(admin_uuid)])

    repo = _FakeJobRepository(fail_user_ids={user_uuid})
    service = JobService(JobConfig(), repo, profile_source=None)

    await service.create_chat_job(user_id=user_uuid, thread_id="thread-2", text="hello")

    assert repo.seen_user_ids[0] == user_uuid
    assert repo.seen_user_ids[1] == admin_uuid
