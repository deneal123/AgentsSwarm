"""Maintenance Celery tasks for periodic housekeeping.

Scheduled via Celery Beat (beat_schedule.py).

Tasks:
  - cleanup_expired_sessions      — удаление истёкших гостевых сессий из БД
  - cleanup_old_tasks             — удаление старых завершённых задач из БД
  - cleanup_completed_queue_entries — удаление старых записей очереди pipeline
  - cleanup_old_files / archive_old_files — удаление старых загруженных файлов
  - cleanup_old_streams           — очистка устаревших ключей из Redis (при наличии)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from celery import shared_task

from service.infrastructure.messaging.tasks.base_task import BaseTask
from service.infrastructure.messaging.utils import run_async_in_sync

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_pg():
    """Lazy-import PgConnector from container (avoids circular import at module level)."""
    from service.container import build, get, has, PgConnectorName
    from service.settings import Config

    if not has(PgConnectorName):
        build(Config())

    return get(PgConnectorName)


# ---------------------------------------------------------------------------
# cleanup_expired_sessions
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    base=BaseTask,
    name="service.infrastructure.messaging.tasks.maintenance_tasks.cleanup_expired_sessions",
    time_limit=180,
    soft_time_limit=160,
)
def cleanup_expired_sessions(self) -> dict:
    """Удалить истёкшие гостевые сессии из profile.guest_session."""
    logger.info("Maintenance: cleanup_expired_sessions — start")

    async def _run():
        pg = _get_pg()
        now = datetime.now(timezone.utc)

        async with pg.get_session_context() as session:
            result = await session.execute(
                sa.text(
                    "DELETE FROM profile.guest_session WHERE expires_at < :now"
                ),
                {"now": now},
            )
            deleted = result.rowcount
            await session.commit()

        logger.info("cleanup_expired_sessions: removed %d expired guest sessions", deleted)
        return {"status": "success", "deleted_count": deleted}

    try:
        return run_async_in_sync(_run)
    except Exception as exc:
        logger.exception("cleanup_expired_sessions failed: %s", exc)
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# cleanup_old_tasks
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    base=BaseTask,
    name="service.infrastructure.messaging.tasks.maintenance_tasks.cleanup_old_tasks",
    time_limit=300,
    soft_time_limit=280,
)
def cleanup_old_tasks(self, days: int = 30) -> dict:
    """Удалить завершённые/отменённые/проваленные задачи старше N дней."""
    logger.info("Maintenance: cleanup_old_tasks (days=%d) — start", days)

    async def _run():
        pg = _get_pg()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        async with pg.get_session_context() as session:
            result = await session.execute(
                sa.text(
                    """
                    DELETE FROM profile.tasks
                    WHERE completed_at < :cutoff
                      AND status IN ('completed', 'failed', 'cancelled')
                    """
                ),
                {"cutoff": cutoff},
            )
            deleted = result.rowcount
            await session.commit()

        logger.info(
            "cleanup_old_tasks: removed %d tasks older than %d days",
            deleted, days,
        )
        return {"status": "success", "deleted_count": deleted, "cutoff": cutoff.isoformat()}

    try:
        return run_async_in_sync(_run)
    except Exception as exc:
        logger.exception("cleanup_old_tasks failed: %s", exc)
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# cleanup_completed_queue_entries
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    base=BaseTask,
    name="service.infrastructure.messaging.tasks.maintenance_tasks.cleanup_completed_queue_entries",
    time_limit=180,
    soft_time_limit=160,
)
def cleanup_completed_queue_entries(self, days: int = 7) -> dict:
    """Удалить завершённые записи очереди pipeline старше N дней.

    Таблица: profile.pipeline_queue (PipelineSlot).
    Удаляются только записи со статусом completed/cancelled/failed.
    """
    logger.info("Maintenance: cleanup_completed_queue_entries (days=%d) — start", days)

    async def _run():
        pg = _get_pg()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        async with pg.get_session_context() as session:
            # Join with tasks to get completed_at; delete old finished slots
            result = await session.execute(
                sa.text(
                    """
                    DELETE FROM profile.pipeline_queue pq
                    USING profile.tasks t
                    WHERE pq.task_id = t.id
                      AND pq.status IN ('completed', 'cancelled', 'failed')
                      AND t.completed_at < :cutoff
                    """
                ),
                {"cutoff": cutoff},
            )
            deleted = result.rowcount
            await session.commit()

        logger.info(
            "cleanup_completed_queue_entries: removed %d old queue entries",
            deleted,
        )
        return {"status": "success", "deleted_count": deleted}

    try:
        return run_async_in_sync(_run)
    except Exception as exc:
        logger.exception("cleanup_completed_queue_entries failed: %s", exc)
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# archive_old_files  (alias: cleanup_old_files для beat_schedule)
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    base=BaseTask,
    name="service.infrastructure.messaging.tasks.maintenance_tasks.archive_old_files",
    time_limit=600,
    soft_time_limit=570,
)
def archive_old_files(self, days: int = 90) -> dict:
    """Удалить записи о загруженных файлах (и физические файлы) старше N дней.

    Физические файлы удаляются через FileSaverService, чтобы поддерживался
    как локальный storage, так и MinIO/S3.
    """
    logger.info("Maintenance: archive_old_files (days=%d) — start", days)

    async def _run():
        pg = _get_pg()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        archived = 0
        errors = 0

        async with pg.get_session_context() as session:
            rows = (
                await session.execute(
                    sa.text(
                        """
                        SELECT id, file_path, file_name
                        FROM profile.file
                        WHERE created_at < :cutoff
                        ORDER BY created_at
                        LIMIT 500
                        """
                    ),
                    {"cutoff": cutoff},
                )
            ).fetchall()

        if not rows:
            return {"status": "success", "archived_count": 0}

        # Try to delete physical files via FileSaverService
        try:
            from service.container import get, FileSaverServiceName
            file_saver = get(FileSaverServiceName)
        except Exception:
            file_saver = None

        ids_to_delete = []
        for row in rows:
            file_id = row[0]
            if file_saver is not None:
                try:
                    await file_saver.delete_file(file_id)
                except Exception as exc:
                    logger.warning("Could not delete file %s: %s", file_id, exc)
                    errors += 1
                    continue
            ids_to_delete.append(str(file_id))
            archived += 1

        if ids_to_delete:
            async with pg.get_session_context() as session:
                await session.execute(
                    sa.text(
                        "DELETE FROM profile.file WHERE id = ANY(:ids::uuid[])"
                    ),
                    {"ids": ids_to_delete},
                )
                await session.commit()

        logger.info(
            "archive_old_files: archived %d, errors %d (cutoff=%s)",
            archived, errors, cutoff.isoformat(),
        )
        return {
            "status": "success",
            "archived_count": archived,
            "error_count": errors,
            "cutoff": cutoff.isoformat(),
        }

    try:
        return run_async_in_sync(_run)
    except Exception as exc:
        logger.exception("archive_old_files failed: %s", exc)
        return {"status": "error", "error": str(exc)}


# Alias для обратной совместимости с beat_schedule
cleanup_old_files = archive_old_files


# ---------------------------------------------------------------------------
# cleanup_old_streams
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    base=BaseTask,
    name="service.infrastructure.messaging.tasks.maintenance_tasks.cleanup_old_streams",
    time_limit=120,
    soft_time_limit=100,
)
def cleanup_old_streams(self) -> dict:
    """Очистить устаревшие ключи из Redis (при наличии подключения).

    Удаляет ключи кэша по паттерну `cache:*`, у которых истёк TTL
    (Redis автоматически удаляет по TTL, но lazy eviction может
    оставлять ключи в памяти — принудительный SCAN ускоряет это).
    На практике просто делает PING для проверки живости соединения
    и сканирует стёкшие сессионные ключи.
    """
    logger.info("Maintenance: cleanup_old_streams — start")

    try:
        from service.container import has, get, RedisClientName

        if not has(RedisClientName):
            logger.info("cleanup_old_streams: Redis not configured, skipping")
            return {"status": "skipped", "reason": "redis_not_configured"}

        redis_client = get(RedisClientName)
        redis_client.ping()

        # Scan for expired session keys (pattern: guest_session:*)
        cleaned = 0
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(
                cursor, match="guest_session:*", count=200
            )
            for key in keys:
                ttl = redis_client.ttl(key)
                if ttl == -1:  # no expiry set — remove stale entries
                    redis_client.delete(key)
                    cleaned += 1
            if cursor == 0:
                break

        logger.info("cleanup_old_streams: cleaned %d stale Redis keys", cleaned)
        return {"status": "success", "cleaned_count": cleaned}

    except Exception as exc:
        logger.warning("cleanup_old_streams failed (non-critical): %s", exc)
        return {"status": "error", "error": str(exc)}
