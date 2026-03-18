"""Base Celery task classes for pushi service.

Defines PushiBaseTask (and BaseTask alias) used by all Celery tasks.
"""

from __future__ import annotations

import logging

from celery import Task

logger = logging.getLogger(__name__)


class PushiBaseTask(Task):
    """Base class for all pushi Celery tasks.

    Provides unified logging on task lifecycle events (failure, retry, success)
    and a helper to retrieve the task name for structured log output.
    """

    abstract = True

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def on_failure(self, exc: Exception, task_id: str, args, kwargs, einfo) -> None:
        logger.error(
            "Task %s[%s] failed: %s",
            self.name,
            task_id,
            exc,
            exc_info=einfo,
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_retry(self, exc: Exception, task_id: str, args, kwargs, einfo) -> None:
        logger.warning(
            "Task %s[%s] retrying due to: %s",
            self.name,
            task_id,
            exc,
        )
        super().on_retry(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id: str, args, kwargs) -> None:
        logger.info("Task %s[%s] succeeded.", self.name, task_id)
        super().on_success(retval, task_id, args, kwargs)


# Alias kept for backward compatibility with maintenance_tasks and __init__
BaseTask = PushiBaseTask
