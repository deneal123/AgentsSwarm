"""
Low-priority worker for maintenance tasks.

This worker handles background cleanup, archiving, and
maintenance operations with relaxed performance requirements.
"""

import logging

from service.infrastructure.messaging.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class MaintenanceWorker(BaseWorker):
    """
    Low-priority worker for maintenance tasks.

    Optimized for:
    - Background processing (lower concurrency)
    - Higher prefetch for throughput
    - More tasks per child (stable long-running tasks)
    - Relaxed time limits
    """

    queue = "maintenance"
    concurrency = 2  # 2 concurrent processes (lower priority)
    prefetch_multiplier = 2  # Prefetch 2 tasks per worker
    max_tasks_per_child = 50  # Can handle more tasks before restart
    time_limit = 600  # 10 minutes hard limit
    soft_time_limit = 540  # 9 minutes soft limit

    def get_queue_name(self) -> str:
        """Get the queue name for maintenance tasks."""
        return self.queue

    def start(self):
        """Start the maintenance worker with background settings."""
        logger.info(
            f"Starting {self.__class__.__name__} with background settings: "
            f"concurrency={self.concurrency}, prefetch={self.prefetch_multiplier}"
        )
        super().start()


# CLI entry point for starting maintenance worker
def start_maintenance_worker():
    """
    CLI entry point for starting maintenance worker.

    Usage:
        python -m service.infrastructure.messaging.workers.maintenance_worker
    """
    from service.infrastructure.messaging.app.celery_app import celery_app

    worker = MaintenanceWorker(celery_app)
    worker.start()


if __name__ == "__main__":
    start_maintenance_worker()
