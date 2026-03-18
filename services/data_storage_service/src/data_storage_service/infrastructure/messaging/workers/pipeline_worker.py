"""Pipeline worker for dataset analysis tasks.

Handles dataset processing through Pipeline.
Concurrency is dynamically managed by TaskOrchestratorService based on
max_parallel_batches from task config (up to max_project_threads).
"""

import logging

from service.infrastructure.messaging.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class PipelineWorker(BaseWorker):
    """Worker for pipeline tasks (dataset analysis).

    Dynamic concurrency: Tasks specify required threads via max_parallel_batches.
    Each pipeline task can use 1-N threads depending on user config.
    
    Config:
    - High max concurrency to handle multiple parallel tasks
    - Each task uses threads specified in its config
    - Longer time limits for dataset processing
    """

    queue = "pipeline"
    # High concurrency - actual thread usage controlled by TaskOrchestratorService
    concurrency = 10  # Can handle up to 10 concurrent tasks
    prefetch_multiplier = 1  # Prefetch 1 task at a time
    max_tasks_per_child = 20  # Restart after 20 tasks (high memory usage)
    time_limit = 7200  # 2 hours hard limit (for large datasets)
    soft_time_limit = 6600  # 1 hour 50 minutes soft limit

    def get_queue_name(self) -> str:
        """Get the queue name for pipeline tasks."""
        return self.queue

    def start(self):
        """Start the pipeline worker."""
        logger.info(
            f"Starting {self.__class__.__name__}: "
            f"queue={self.queue}, max_concurrency={self.concurrency} "
            f"(actual threads per task controlled by TaskOrchestratorService)"
        )
        super().start()


# CLI entry point for starting pipeline worker
def start_pipeline_worker():
    """CLI entry point for starting pipeline worker.

    Usage:
        python -m service.infrastructure.messaging.workers.pipeline_worker
    """
    from service.infrastructure.messaging.app.celery_app import celery_app

    worker = PipelineWorker(celery_app)
    worker.start()


if __name__ == "__main__":
    start_pipeline_worker()
