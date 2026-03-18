import logging
import os
import sys
from typing import Any

from service.infrastructure.database.postgresql import PgConnector
from service.infrastructure.scanning import BasicFileScanner
from service.repositories.auth_repository import AuthRepository
from service.repositories.file_repository import FileRepository
from service.repositories.profile_repository import ProfileRepository
from service.repositories.pipeline_slot_repository import PipelineSlotRepository
from service.repositories.rule_repository import RuleRepository
from service.repositories.task_concurrency_repository import TaskConcurrencyRepository
from service.repositories.task_repository import TaskRepository
from service.repositories.communication_result_repository import CommunicationResultRepository
from service.services.auth_service import AuthService
from service.services.file_saver_service import FileSaverService
from service.services.profile_service import ProfileService
from service.services.rule_service import RuleService
from service.services.pushi_service import PlaygroundService, PipelineService
from service.services.task_orchestrator_service import TaskOrchestratorService
from service.services.task_service import TaskService
from service.services.communication_result_service import CommunicationResultService
from service.logics.playground_logic import PlaygroundLogic
from service.logics.pipeline_logic import PipelineLogic
from service.logics.file_logic import FileLogic

from service.settings import Config
from service.utils.background_task_manager import BackgroundTaskManager

logger = logging.getLogger(__name__)

_CONTAINER: dict[str, Any] = {}

storage: Any


def build(config: Config):
    _CONTAINER.clear()
    _CONTAINER[BackgroundTaskManagerName] = BackgroundTaskManager()
    _CONTAINER[PgConnectorName] = PgConnector(config.pg)

    redis_cache = None
    redis_session_store = None
    redis_client = None

    if getattr(config, "redis", None) and config.redis.enabled:
        try:
            from service.infrastructure.cache.redis_cache import RedisCacheService
            from service.infrastructure.cache.redis_manager import RedisManager
            from service.infrastructure.cache.redis_session_store import RedisSessionStore
            from service.repositories.decorators import set_redis_cache

            redis_manager = RedisManager(config.redis)
            redis_client = redis_manager.get_client()

            _CONTAINER[RedisManagerName] = redis_manager
            _CONTAINER[RedisClientName] = redis_client

            redis_cache = RedisCacheService(redis_client, config.redis)
            redis_session_store = RedisSessionStore(redis_client, config.redis)

            _CONTAINER[RedisCacheServiceName] = redis_cache
            _CONTAINER[RedisSessionStoreName] = redis_session_store

            set_redis_cache(redis_cache)

            logger.info("Initialized Redis cache and session backends")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to initialize Redis backend: %s", exc)
    else:
        logger.info("Redis backend disabled via configuration")

    # Repositories
    _CONTAINER[AuthRepositoryName] = AuthRepository(
        get(PgConnectorName), session_store=redis_session_store
    )
    _CONTAINER[TaskRepositoryName] = TaskRepository(get(PgConnectorName))
    _CONTAINER[TaskConcurrencyRepositoryName] = TaskConcurrencyRepository(get(PgConnectorName))
    _CONTAINER[PipelineSlotRepositoryName] = PipelineSlotRepository(get(PgConnectorName))
    _CONTAINER[ProfileRepositoryName] = ProfileRepository(get(PgConnectorName))
    _CONTAINER[FileRepositoryName] = FileRepository(get(PgConnectorName))
    _CONTAINER[RuleRepositoryName] = RuleRepository(get(PgConnectorName))
    _CONTAINER[CommunicationResultRepositoryName] = CommunicationResultRepository(get(PgConnectorName))

    # Services
    _CONTAINER[ProfileServiceName] = ProfileService(
        get(ProfileRepositoryName),
        cache=redis_cache,
        cache_ttl_seconds=(
            config.redis.profile_cache_ttl_seconds if redis_cache and config.redis else None
        ),
        server_config=config.servers,
    )
    _CONTAINER[AuthServiceName] = AuthService(
        config.auth,
        get(AuthRepositoryName),
        get(ProfileServiceName),
    )
    _CONTAINER[TaskServiceName] = TaskService(
        config.task,
        get(TaskRepositoryName),
    )
    _CONTAINER[PlaygroundServiceName] = PlaygroundService()
    _CONTAINER[PipelineServiceName] = PipelineService()

    # Storage backend selection — must come before FileSaverService and TaskOrchestratorService
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
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "Failed to initialize %s storage backend, falling back to local: %s", backend, e
        )
        from service.infrastructure.storage.local_file_storage import LocalFileStorage

        storage = LocalFileStorage()
        logger.info("Fallback: Using Local storage backend")

    # Provide FileScanner implementation
    try:
        _CONTAINER["FileScanner"] = BasicFileScanner(storage)
        logger.info("Initialized FileScanner service")
    except Exception:
        logger.warning("Failed to initialize FileScanner service")

    _CONTAINER[FileSaverServiceName] = FileSaverService(
        repository=get(FileRepositoryName),
        folder_name="uploads",
        file_storage=storage,
    )

    _CONTAINER[TaskOrchestratorServiceName] = TaskOrchestratorService(
        config=config.task,
        repository=get(TaskRepositoryName),
        concurrency_repository=get(TaskConcurrencyRepositoryName),
        queue_repository=get(PipelineSlotRepositoryName),
        file_repository=get(FileRepositoryName),
        file_saver_service=get(FileSaverServiceName),
        playground_service=get(PlaygroundServiceName),
        pipeline_service=get(PipelineServiceName),
    )
    # RuleService doesn't require a dedicated configuration object.
    _CONTAINER[RuleServiceName] = RuleService(
        get(RuleRepositoryName),
    )
    _CONTAINER[CommunicationResultServiceName] = CommunicationResultService(
        get(CommunicationResultRepositoryName),
    )

    # Logic layer
    _CONTAINER[PlaygroundLogicName] = PlaygroundLogic()
    _CONTAINER[PipelineLogicName] = PipelineLogic()
    _CONTAINER[FileLogicName] = FileLogic()

    if os.getenv("CELERY_BROKER_URL"):
        try:
            from service.infrastructure.messaging.app.celery_app import celery_app
            from service.infrastructure.messaging.workers.worker_manager import WorkerManager

            _CONTAINER[CeleryAppName] = celery_app
            _CONTAINER[WorkerManagerName] = WorkerManager(celery_app)
            logger.info("Initialized Celery app and WorkerManager for background task processing")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to initialize Celery app and WorkerManager: %s", exc)


def getter(name: str):
    return lambda: get(name)


def get(name: str):
    if name not in _CONTAINER:
        raise ValueError(f"Dependency not found: {name}")
    return _CONTAINER[name]


def has(name: str) -> bool:
    return name in _CONTAINER


# Service names and types
AuthServiceT = AuthService
AuthServiceName = "AuthService"

TaskServiceT = TaskService
TaskServiceName = "TaskService"

TaskOrchestratorServiceT = TaskOrchestratorService
TaskOrchestratorServiceName = "TaskOrchestratorService"

PlaygroundServiceT = PlaygroundService
PlaygroundServiceName = "PlaygroundService"

PipelineServiceT = PipelineService
PipelineServiceName = "PipelineService"

ProfileServiceT = ProfileService
ProfileServiceName = "ProfileService"

FileSaverServiceT = FileSaverService
FileSaverServiceName = "FileSaverService"

RuleServiceT = RuleService
RuleServiceName = "RuleService"

CommunicationResultRepositoryName = "CommunicationResultRepository"
CommunicationResultServiceT = CommunicationResultService
CommunicationResultServiceName = "CommunicationResultService"


# Repository names
AuthRepositoryName = "AuthRepository"
TaskRepositoryName = "TaskRepository"
TaskConcurrencyRepositoryName = "TaskConcurrencyRepository"
PipelineSlotRepositoryName = "PipelineSlotRepository"
ProfileRepositoryName = "ProfileRepository"
FileRepositoryName = "FileRepository"
RuleRepositoryName = "RuleRepository"

# Utils names
BackgroundTaskManagerT = BackgroundTaskManager
BackgroundTaskManagerName = "BackgroundTaskManager"
FileScannerName = "FileScanner"
PgConnectorName = "PgConnector"

# Redis related names
RedisManagerName = "RedisManager"
RedisClientName = "RedisClient"
RedisCacheServiceName = "RedisCacheService"
RedisSessionStoreName = "RedisSessionStore"

# Celery related names
CeleryAppName = "CeleryApp"
WorkerManagerName = "WorkerManager"

# Logic layer names
PlaygroundLogicName = "PlaygroundLogic"
PipelineLogicName = "PipelineLogic"
FileLogicName = "FileLogic"


# ============================================================================
# Module-level accessor functions (used by logic layer via self.container.xxx())
# ============================================================================

def task_orchestrator_service():
    return get(TaskOrchestratorServiceName)


def rule_service():
    return get(RuleServiceName)


def file_repository():
    return get(FileRepositoryName)


def file_saver_service():
    return get(FileSaverServiceName)


def pipeline_slot_repository():
    return get(PipelineSlotRepositoryName)


def playground_service():
    return get(PlaygroundServiceName)


def pipeline_service():
    return get(PipelineServiceName)


def task_service():
    return get(TaskServiceName)


def task_repository():
    return get(TaskRepositoryName)


def task_concurrency_repository():
    return get(TaskConcurrencyRepositoryName)


def profile_service():
    return get(ProfileServiceName)


def auth_service():
    return get(AuthServiceName)


def communication_result_repository():
    return get(CommunicationResultRepositoryName)


def communication_result_service():
    return get(CommunicationResultServiceName)


# Expose this module as 'container' so logic layer can do:
#   from service.container import container
#   self.container.task_orchestrator_service()
container = sys.modules[__name__]
