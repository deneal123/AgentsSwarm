from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from service.infrastructure.database.postgresql import PgConnector
from service.infrastructure.messaging.ports import CeleryJobQueuePort, RedisListMessageBusPort, RedisStreamPort
from service.services.profile.persistence.auth_repository import AuthRepository
from service.services.files.persistence.file_repository import FileRepository
from service.services.jobs.persistence.job_repository import JobRepository
from service.services.profile.persistence.profile_repository import ProfileRepository
from service.services.chat.domain.process_chat_message_handler import ProcessChatMessageHandler
from service.services.files.application.file_saver_service import FileSaverService
from service.services.files.application.file_scanner_service import BasicFileScanner
from service.services.jobs.application.job_processor import NewJobProcessor
from service.services.jobs.application.job_service import JobService
from service.services.profile.application.auth_service import AuthService
from service.services.profile.application.profile_service import ProfileService
from service.services.analytics.application.analytics_service import AnalyticsService
from service.utils.background_task_manager import BackgroundTaskManager


@dataclass(slots=True)
class InfraContainer:
    background_task_manager: BackgroundTaskManager
    pg_connector: PgConnector
    stream_port: RedisStreamPort
    message_bus_port: RedisListMessageBusPort
    job_queue_port: CeleryJobQueuePort
    redis_manager: Any | None = None
    redis_client: Any | None = None
    redis_cache: Any | None = None
    redis_session_store: Any | None = None
    storage: Any | None = None
    file_scanner: BasicFileScanner | None = None
    celery_app: Any | None = None


@dataclass(slots=True)
class RepositoriesContainer:
    auth_repository: AuthRepository
    job_repository: JobRepository
    profile_repository: ProfileRepository
    file_repository: FileRepository


@dataclass(slots=True)
class ServicesContainer:
    profile_service: ProfileService
    auth_service: AuthService
    job_service: JobService
    file_saver_service: FileSaverService
    analytics_service: AnalyticsService
    process_chat_message_handler: ProcessChatMessageHandler
    new_job_processor: NewJobProcessor
    chat_application_service: Any


@dataclass(slots=True)
class AppContainer:
    infra: InfraContainer
    repositories: RepositoriesContainer
    services: ServicesContainer
