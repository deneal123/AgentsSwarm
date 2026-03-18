"""
Scheduler for cleanup and maintenance tasks.

Handles periodic cleanup operations:
- Old tasks cleanup (daily)
- Redis Streams cleanup (hourly)
- Expired sessions cleanup (hourly)
- Old files cleanup (weekly)
- Completed queue entries cleanup (daily)
"""

import logging
from typing import Dict

from celery.schedules import crontab

from service.infrastructure.messaging.schedulers.base_scheduler import BaseScheduler

logger = logging.getLogger(__name__)


class CleanupScheduler(BaseScheduler):
    """
    Scheduler for cleanup and maintenance tasks.

    Manages periodic cleanup operations to maintain system health
    and prevent resource exhaustion.
    """

    def get_schedule(self) -> Dict:
        """
        Get cleanup task schedule.

        Returns:
            dict: Schedule configuration for Celery Beat
        """
        schedule = {
            # Daily task cleanup at 3 AM
            "cleanup-old-tasks": {
                "task": "service.infrastructure.messaging.tasks.maintenance_tasks.cleanup_old_tasks",
                "schedule": crontab(hour=3, minute=0),  # Daily at 3:00 AM
                "args": (30,),  # Keep last 30 days
                "options": {
                    "queue": "maintenance",
                    "priority": 3,
                },
            },
            # Hourly Redis Streams cleanup
            "cleanup-old-streams": {
                "task": "service.infrastructure.messaging.tasks.maintenance_tasks.cleanup_old_streams",
                "schedule": crontab(minute=0),  # Every hour
                "args": (),
                "options": {
                    "queue": "maintenance",
                    "priority": 5,
                },
            },
            # Hourly expired sessions cleanup
            "cleanup-expired-sessions": {
                "task": "service.infrastructure.messaging.tasks.maintenance_tasks.cleanup_expired_sessions",
                "schedule": crontab(minute=15),  # Every hour at :15
                "args": (),
                "options": {
                    "queue": "maintenance",
                    "priority": 4,
                },
            },
            # Weekly old files cleanup on Sunday at 4 AM
            "cleanup-old-files": {
                "task": "service.infrastructure.messaging.tasks.maintenance_tasks.cleanup_old_files",
                "schedule": crontab(hour=4, minute=0, day_of_week=0),  # Sunday 4:00 AM
                "args": (90,),  # Cleanup files older than 90 days
                "options": {
                    "queue": "maintenance",
                    "priority": 2,
                },
            },
            # Daily cleanup of completed queue entries at 2 AM
            "cleanup-completed-queue": {
                "task": "service.infrastructure.messaging.tasks.maintenance_tasks.cleanup_completed_queue_entries",
                "schedule": crontab(hour=2, minute=0),  # Daily at 2:00 AM
                "args": (7,),  # Keep last 7 days
                "options": {
                    "queue": "maintenance",
                    "priority": 3,
                },
            },
            # Process pending queue entries every 5 minutes
            "process-pending-queue": {
                "task": "service.infrastructure.messaging.tasks.pushi_tasks.process_pending_queue_entries",
                "schedule": crontab(minute="*/5"),  # Every 5 minutes
                "args": (10,),  # Process up to 10 entries
                "options": {
                    "queue": "queue",
                    "priority": 8,
                },
            },
        }

        if self.validate_schedule(schedule):
            logger.info(f"CleanupScheduler configured with {len(schedule)} tasks")
            return schedule

        return {}


# Standalone function to get cleanup schedule
def get_cleanup_schedule() -> Dict:
    """
    Get cleanup schedule configuration.

    Returns:
        dict: Schedule configuration for Celery Beat
    """
    scheduler = CleanupScheduler()
    return scheduler.get_schedule()
