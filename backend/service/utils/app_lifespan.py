import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from service.container import (
    build_container,
    get_current_container,
    set_current_container,
)
from service.settings import Config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")

    try:
        app_container = getattr(app.state, "container", None)
        if app_container is None:
            config = Config()
            logger.info("Building dependency container...")
            app_container = build_container(config)
            app.state.container = app_container
        set_current_container(app_container)

        logger.info("Initializing database...")
        await app_container.infra.pg_connector.verify_connection()
        logger.info("Database connection verified")

        logger.info("Starting background task manager...")
        task_manager = app_container.infra.background_task_manager
        await task_manager.start()

        try:
            await task_manager.start_task_with_restart(
                app_container.services.new_job_processor.process_new_jobs,
                task_name="new-jobs-processor",
                restart_delay=5,
            )
        except Exception:
            logger.warning("Job processor is not available; background processing disabled")

        try:
            from service.utils.file_scan_worker import scan_loop

            await task_manager.start_task_with_restart(
                scan_loop,
                task_name="file-scan-loop",
                restart_delay=5,
            )
        except Exception:
            logger.warning("File scanner loop is not available; file scanning disabled")

        logger.info("Application started successfully!")
        yield

    except Exception as exc:
        logger.error("Failed to start application: %s", exc)
        raise

    finally:
        logger.info("Shutting down TeleRAG application...")

        try:
            active_container = getattr(app.state, "container", None) or get_current_container()
            logger.info("Stopping background task manager...")
            await active_container.infra.background_task_manager.stop()

            logger.info("Closing database connections...")
            await active_container.infra.pg_connector.close()
            logger.info("Application shut down gracefully")

        except Exception as exc:
            logger.error("Error during shutdown: %s", exc)


async def health_check():
    try:
        app_container = get_current_container()
        await app_container.infra.pg_connector.verify_connection()

        return {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0",
        }

    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        return {"status": "unhealthy", "error": str(exc), "version": "1.0.0"}
