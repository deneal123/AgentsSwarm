"""Application lifespan management with graceful startup/shutdown."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from service import container
from service.presentation.websocket_manager import ws_manager
from service.settings import Config

logger = logging.getLogger(__name__)
SHUTDOWN_TIMEOUT = 30


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of the backend application."""

    logger.info("Starting Backend...")

    config = Config()

    redis_client = None
    task_manager = None
    pg_connector = None

    try:
        logger.info("Building dependency container...")
        container.build(config)
        logger.info("Dependency container built")

        logger.info("Initializing database connections...")
        pg_connector = container.get(container.PgConnectorName)
        await pg_connector.verify_connection()
        logger.info("Database connection verified")

        logger.info("Starting background task manager...")
        task_manager = container.get(container.BackgroundTaskManagerName)
        await task_manager.start()
        logger.info("Background task manager started")
    except Exception as exc:
        logger.exception("CRITICAL: Failed to initialize application: %s", exc)
        raise

    try:
        if container.has(container.RedisClientName):
            try:
                redis_client = container.get(container.RedisClientName)
                await redis_client.ping()
                logger.info("Redis connection established")
            except Exception as exc:
                logger.warning("Redis not available: %s", exc)
        else:
            logger.warning("Redis not available: dependency RedisClient not registered")

        logger.info("Application started successfully!")

        yield
    finally:
        logger.info("Shutting down application...")

        try:
            await asyncio.wait_for(
                ws_manager.close_all_connections(code=1001, reason="Server shutdown"),
                timeout=10,
            )
            logger.info("WebSocket connections closed")
        except asyncio.TimeoutError:
            logger.warning("WebSocket shutdown timed out")
        except Exception as exc:
            logger.warning("Error closing WebSockets: %s", exc)

        if container.has(container.WorkerManagerName):
            try:
                worker_manager = container.get(container.WorkerManagerName)
                worker_manager.stop_all_workers()
                logger.info("✓ Celery workers stopped")
            except Exception as exc:
                logger.warning("Celery workers cleanup skipped: %s", exc)

        if task_manager:
            try:
                await asyncio.wait_for(task_manager.stop(), timeout=15)
                logger.info("Background tasks stopped")
            except asyncio.TimeoutError:
                logger.warning("Background task shutdown timed out")
            except Exception as exc:
                logger.warning("Error stopping background tasks: %s", exc)

        if pg_connector:
            try:
                await pg_connector.close()
                logger.info("Database connections closed")
            except Exception as exc:
                logger.warning("Error closing database: %s", exc)

        if redis_client:
            try:
                await redis_client.close()
                logger.info("Redis connections closed")
            except Exception as exc:
                logger.warning("Error closing Redis: %s", exc)

        logger.info("Application shut down gracefully")


async def health_check() -> dict[str, str | dict]:
    """Simple health check reporting database/Redis status."""

    status = "healthy"
    details: dict[str, str] = {}

    try:
        if container.has(container.PgConnectorName):
            pg = container.get(container.PgConnectorName)
            await pg.verify_connection()
            details["postgres"] = "ok"
        else:
            details["postgres"] = "unavailable"
            status = "unhealthy"
    except Exception as exc:
        status = "unhealthy"
        details["postgres"] = str(exc)

    if container.has(container.RedisClientName):
        try:
            redis = container.get(container.RedisClientName)
            await redis.ping()
            details["redis"] = "ok"
        except Exception as exc:
            status = "unhealthy"
            details["redis"] = str(exc)
    else:
        details["redis"] = "disabled"

    return {
        "status": status,
        "details": details
    }
