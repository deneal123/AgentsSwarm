"""Playground worker for communication analysis tasks.

Handles single and batch communication processing.
Concurrency is dynamically managed by TaskOrchestratorService based on
max_parallel_batches from task config (up to max_project_threads).
"""

import logging

from service.infrastructure.messaging.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class PlaygroundWorker(BaseWorker):
    """Worker for playground tasks (communication analysis).

    Dynamic concurrency: Tasks specify required threads via max_parallel_batches.
    Worker handles task execution while TaskOrchestratorService manages thread allocation.
    
    Config:
    - High max concurrency to handle multiple parallel tasks
    - Each task uses threads specified in its config (capped at max_project_threads)
    """

    queue = "playground"
    # High concurrency - actual thread usage controlled by TaskOrchestratorService
    concurrency = 10  # Can handle up to 10 concurrent tasks
    prefetch_multiplier = 1  # Prefetch 1 task per worker process
    max_tasks_per_child = 50  # Restart after 50 tasks
    time_limit = 600  # 10 minutes hard limit (for large batches)
    soft_time_limit = 540  # 9 minutes soft limit

    def get_queue_name(self) -> str:
        """Get the queue name for playground tasks."""
        return self.queue

    def start(self):
        """Start the playground worker."""
        logger.info(
            f"Starting {self.__class__.__name__}: "
            f"queue={self.queue}, max_concurrency={self.concurrency} "
            f"(actual threads per task controlled by TaskOrchestratorService)"
        )
        super().start()


# CLI entry point for starting playground worker
def start_playground_worker():
    """CLI entry point for starting playground worker.

    Usage:
        python -m service.infrastructure.messaging.workers.playground_worker
    """
    from service.infrastructure.messaging.app.celery_app import celery_app

    worker = PlaygroundWorker(celery_app)
    worker.start()


if __name__ == "__main__":
    start_playground_worker()
