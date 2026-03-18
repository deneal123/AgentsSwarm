"""
Base worker class for Celery workers.

Provides common functionality for all workers:
- Configuration management
- Graceful shutdown handling
- Health check capabilities
- Worker statistics tracking
"""

import logging
import signal
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """
    Base class for Celery workers.

    Attributes:
        queue (str): Queue name that worker consumes from
        concurrency (int): Number of concurrent worker processes/threads
        prefetch_multiplier (int): How many messages to prefetch per worker
        max_tasks_per_child (int): Max tasks before worker process restart
        time_limit (int): Hard time limit for task execution (seconds)
        soft_time_limit (int): Soft time limit for task execution (seconds)
    """

    queue: str = "default"
    concurrency: int = 4
    prefetch_multiplier: int = 1
    max_tasks_per_child: int = 100
    time_limit: int = 300  # 5 minutes
    soft_time_limit: int = 270  # 4.5 minutes

    def __init__(self, celery_app=None):
        """
        Initialize worker.

        Args:
            celery_app: Celery application instance
        """
        self.celery_app = celery_app
        self._shutdown_requested = False
        self._setup_signal_handlers()

        logger.info(
            f"Initialized {self.__class__.__name__}: "
            f"queue={self.queue}, concurrency={self.concurrency}, "
            f"prefetch={self.prefetch_multiplier}, max_tasks={self.max_tasks_per_child}"
        )

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal gracefully."""
        logger.info(f"{self.__class__.__name__} received shutdown signal {signum}")
        self._shutdown_requested = True

    def get_worker_options(self) -> dict:
        """
        Get worker configuration options.

        Returns:
            dict: Worker configuration for Celery
        """
        return {
            "queues": [self.queue],
            "concurrency": self.concurrency,
            "prefetch_multiplier": self.prefetch_multiplier,
            "max_tasks_per_child": self.max_tasks_per_child,
            "task_time_limit": self.time_limit,
            "task_soft_time_limit": self.soft_time_limit,
            "worker_lost_wait": 10.0,
            "worker_max_tasks_per_child": self.max_tasks_per_child,
        }

    def start(self):
        """
        Start the worker.

        This method should be implemented by subclasses if custom
        startup logic is needed.
        """
        if not self.celery_app:
            raise ValueError("Celery app not provided")

        logger.info(f"Starting {self.__class__.__name__}...")
        options = self.get_worker_options()

        # Start worker with configured options
        worker = self.celery_app.Worker(**options)
        worker.start()

    def stop(self, timeout: int = 30):
        """
        Stop the worker gracefully.

        Args:
            timeout: Maximum time to wait for graceful shutdown (seconds)
        """
        logger.info(f"Stopping {self.__class__.__name__} (timeout={timeout}s)...")
        self._shutdown_requested = True

    def is_healthy(self) -> bool:
        """
        Check if worker is healthy.

        Returns:
            bool: True if worker is healthy
        """
        return not self._shutdown_requested

    @abstractmethod
    def get_queue_name(self) -> str:
        """
        Get the queue name for this worker.

        Returns:
            str: Queue name
        """
        pass
