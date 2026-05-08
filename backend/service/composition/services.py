from __future__ import annotations

from service.composition.models import InfraContainer, RepositoriesContainer, ServicesContainer
from service.services.chat.composition import build_chat_components
from service.services.chat.domain.process_chat_message_handler import ProcessChatMessageHandler
from service.services.chat.persistence.chat_repository import ChatRepository
from service.services.files.application.file_saver_service import FileSaverService
from service.services.jobs.application.job_processor import NewJobProcessor
from service.services.jobs.application.job_service import JobService
from service.services.profile.application.auth_service import AuthService
from service.services.profile.application.profile_service import ProfileService
from service.settings import Config


def build_services(
    repos: RepositoriesContainer,
    infra: InfraContainer,
    config: Config,
) -> ServicesContainer:
    profile_service = ProfileService(
        config.profile,
        repos.profile_repository,
        cache=infra.redis_cache,
        cache_ttl_seconds=(
            config.redis.profile_cache_ttl_seconds
            if infra.redis_cache and config.redis
            else None
        ),
    )
    auth_service = AuthService(
        config.auth,
        repos.auth_repository,
        profile_service,
    )
    job_service = JobService(
        config.job,
        repos.job_repository,
        profile_service,
        job_queue=infra.job_queue_port,
    )

    file_saver_service = FileSaverService(
        repository=repos.file_repository,
        folder_name="uploads",
        file_storage=infra.storage,
        message_bus=infra.message_bus_port,
    )

    process_chat_message_handler = ProcessChatMessageHandler(
        job_service=job_service,
        job_queue=infra.job_queue_port,
    )

    new_job_processor = NewJobProcessor(
        config.job,
        repos.job_repository,
    )

    chat_components = build_chat_components(
        repository=ChatRepository(infra.pg_connector),
        job_handler=process_chat_message_handler,
        file_service=file_saver_service,
    )

    return ServicesContainer(
        profile_service=profile_service,
        auth_service=auth_service,
        job_service=job_service,
        file_saver_service=file_saver_service,
        process_chat_message_handler=process_chat_message_handler,
        new_job_processor=new_job_processor,
        chat_application_service=chat_components.application_service,
    )
