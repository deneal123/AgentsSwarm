from __future__ import annotations

import logging
import os
from typing import Any

from service.composition.models import InfraContainer
from service.infrastructure.database.postgresql import PgConnector
from service.infrastructure.messaging.ports import CeleryJobQueuePort, RedisListMessageBusPort, RedisStreamPort
from service.services.files.application.file_scanner_service import BasicFileScanner
from service.settings import Config
from service.utils.background_task_manager import BackgroundTaskManager

logger = logging.getLogger(__name__)


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
        logger.warning("Failed to initialize %s storage backend, falling back to local: %s", backend, exc)
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
