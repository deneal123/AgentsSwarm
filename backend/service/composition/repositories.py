from __future__ import annotations

from service.composition.models import InfraContainer, RepositoriesContainer
from service.repositories.auth_repository import AuthRepository
from service.repositories.file_repository import FileRepository
from service.repositories.job_repository import JobRepository
from service.repositories.profile_repository import ProfileRepository


def build_repositories(infra: InfraContainer) -> RepositoriesContainer:
    return RepositoriesContainer(
        auth_repository=AuthRepository(
            infra.pg_connector,
            session_store=infra.redis_session_store,
        ),
        job_repository=JobRepository(infra.pg_connector),
        profile_repository=ProfileRepository(infra.pg_connector),
        file_repository=FileRepository(infra.pg_connector),
    )
