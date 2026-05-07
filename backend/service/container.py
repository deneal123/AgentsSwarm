import logging
import os
from dataclasses import dataclass
from typing import Any

from fastapi import Request

from service.infrastructure.database.postgresql import PgConnector
from service.infrastructure.messaging.ports import CeleryJobQueuePort, RedisListMessageBusPort, RedisStreamPort
from service.repositories.auth_repository import AuthRepository
from service.repositories.file_repository import FileRepository
from service.repositories.job_repository import JobRepository
from service.repositories.profile_repository import ProfileRepository
from service.services.auth_service import AuthService
from service.services.file_saver_service import FileSaverService
from service.services.file_scanner_service import BasicFileScanner
from service.services.job_processor import NewJobProcessor
from service.services.job_service import JobService
from service.chat.domain.process_chat_message_handler import ProcessChatMessageHandler
from service.services.profile_service import ProfileService
from service.settings import Config
from service.utils.background_task_manager import BackgroundTaskManager

logger = logging.getLogger(__name__)


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
    process_chat_message_handler: ProcessChatMessageHandler
    new_job_processor: NewJobProcessor


@dataclass(slots=True)
class AppContainer:
    infra: InfraContainer
    repositories: RepositoriesContainer
    services: ServicesContainer


_CURRENT_CONTAINER: AppContainer | None = None


def build_infra(config: Config) -> InfraContainer:
    background_task_manager = BackgroundTaskManager()
    pg_connector = PgConnector(config.pg)

    redis_manager = None
    redis_client = None
    redis_cache = None
    redis_session_store = None

    if getattr(config, "redis", None) and config.redis.enabled:
        try:
            from service.infrastructure.cache.redis_cache import RedisCacheService
            from service.infrastructure.cache.redis_manager import RedisManager
            from service.infrastructure.cache.redis_session_store import RedisSessionStore

            redis_manager = RedisManager(config.redis)
            redis_client = redis_manager.get_client()
            redis_cache = RedisCacheService(redis_client, config.redis)
            redis_session_store = RedisSessionStore(redis_client, config.redis)
            logger.info("Initialized Redis cache and session backends")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to initialize Redis backend: %s", exc)
    else:
        logger.info("Redis backend disabled via configuration")

    stream_port = RedisStreamPort(redis_client)
    message_bus_port = RedisListMessageBusPort(redis_client)
    job_queue_port = CeleryJobQueuePort()

    backend = config.storage.backend.strip().lower()
    storage: Any = None
    try:
        if backend == "minio":
            from service.infrastructure.storage.minio_file_storage import MinioFileStorage

            storage = MinioFileStorage(config.minio)
            logger.info("Initialized MinIO storage backend")
        else:
            from service.infrastructure.storage.local_file_storage import LocalFileStorage

            storage = LocalFileStorage()
            logger.info("Initialized Local storage backend")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to initialize %s storage backend, falling back to local: %s", backend, exc
        )
        from service.infrastructure.storage.local_file_storage import LocalFileStorage

        storage = LocalFileStorage()
        logger.info("Fallback: Using Local storage backend")

    file_scanner = None
    try:
        file_scanner = BasicFileScanner(storage)
        logger.info("Initialized FileScanner service")
    except Exception:
        logger.warning("Failed to initialize FileScanner service")

    celery_app = None
    if os.getenv("CELERY_BROKER_URL"):
        try:
            from service.infrastructure.messaging.celery_app import celery_app as initialized_celery_app

            celery_app = initialized_celery_app
            logger.info("Initialized Celery app for background task processing")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to initialize Celery app: %s", exc)

    return InfraContainer(
        background_task_manager=background_task_manager,
        pg_connector=pg_connector,
        stream_port=stream_port,
        message_bus_port=message_bus_port,
        job_queue_port=job_queue_port,
        redis_manager=redis_manager,
        redis_client=redis_client,
        redis_cache=redis_cache,
        redis_session_store=redis_session_store,
        storage=storage,
        file_scanner=file_scanner,
        celery_app=celery_app,
    )


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

    return ServicesContainer(
        profile_service=profile_service,
        auth_service=auth_service,
        job_service=job_service,
        file_saver_service=file_saver_service,
        process_chat_message_handler=process_chat_message_handler,
        new_job_processor=new_job_processor,
    )


def build_container(config: Config) -> AppContainer:
    infra = build_infra(config)
    repositories = build_repositories(infra)
    services = build_services(repositories, infra, config)
    return AppContainer(infra=infra, repositories=repositories, services=services)


def set_current_container(app_container: AppContainer) -> None:
    global _CURRENT_CONTAINER
    _CURRENT_CONTAINER = app_container


def get_current_container() -> AppContainer:
    if _CURRENT_CONTAINER is None:
        raise RuntimeError("Dependency container not initialized")
    return _CURRENT_CONTAINER


def get_app_container(request: Request) -> AppContainer:
    app_container = getattr(request.app.state, "container", None)
    if app_container is not None:
        return app_container
    return get_current_container()


def get_auth_service(request: Request) -> AuthService:
    return get_app_container(request).services.auth_service


def get_job_service(request: Request) -> JobService:
    return get_app_container(request).services.job_service


def get_profile_service(request: Request) -> ProfileService:
    return get_app_container(request).services.profile_service


def get_file_saver_service(request: Request) -> FileSaverService:
    return get_app_container(request).services.file_saver_service


def get_optional_redis_client(request: Request) -> Any:
    return get_app_container(request).infra.redis_client


def get_optional_redis_session_store(request: Request) -> Any:
    return get_app_container(request).infra.redis_session_store
