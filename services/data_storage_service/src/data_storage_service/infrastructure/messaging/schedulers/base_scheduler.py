"""
Base scheduler class for periodic tasks.

Provides common functionality for all schedulers:
- Schedule configuration
- Task triggering
- Error handling
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class BaseScheduler(ABC):
    """
    Base class for task schedulers.

    Schedulers manage periodic tasks using Celery Beat.
    Each scheduler is responsible for a category of tasks.
    """

    def __init__(self, celery_app=None):
        """
        Initialize scheduler.

        Args:
            celery_app: Celery application instance
        """
        self.celery_app = celery_app
        logger.info(f"Initialized {self.__class__.__name__}")

    @abstractmethod
    def get_schedule(self) -> Dict:
        """
        Get the schedule configuration for this scheduler.

        Returns:
            dict: Schedule configuration for Celery Beat

        Example:
            {
                'cleanup-old-chats': {
                    'task': 'service.infrastructure.messaging.tasks.maintenance_tasks.delete_old_chat_history',
                    'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
                    'args': (30,),  # Keep 30 days
                },
            }
        """
        pass

    def validate_schedule(self, schedule: Dict) -> bool:
        """
        Validate schedule configuration.

        Args:
            schedule: Schedule configuration

        Returns:
            bool: True if schedule is valid
        """
        if not schedule:
            logger.warning(f"{self.__class__.__name__}: Empty schedule")
            return False

        for task_name, config in schedule.items():
            if "task" not in config:
                logger.error(f"Task {task_name} missing 'task' key")
                return False

            if "schedule" not in config:
                logger.error(f"Task {task_name} missing 'schedule' key")
                return False

        logger.info(f"{self.__class__.__name__}: Schedule validated ({len(schedule)} tasks)")
        return True

    def get_task_status(self, task_name: str) -> Optional[Dict]:
        """
        Get status of a scheduled task.

        Args:
            task_name: Name of the task

        Returns:
            dict: Task status or None if not found
        """
        # TODO: Query Celery Beat for task status
        logger.warning("get_task_status not yet implemented")
        return None
