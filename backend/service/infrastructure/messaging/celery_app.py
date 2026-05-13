"""Celery application configuration.

This module configures the Celery app for background task processing.
It supports both RabbitMQ as the broker and Redis as the result backend.
"""

import logging
import os

from celery import Celery  # type: ignore[import]

logger = logging.getLogger(__name__)

# Celery configuration from environment variables
CELERY_BROKER_URL = os.getenv("CELERY__BROKER_URL", "amqp://guest:guest@rabbitmq:5672//")
CELERY_RESULT_BACKEND = os.getenv("CELERY__RESULT_BACKEND", "redis://redis:6379/1")

# Create Celery app
celery_app = Celery(
    "eater",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["service.infrastructure.messaging.tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task execution
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,  # Requeue if worker dies
    # Task time limits
    task_soft_time_limit=3600,  # 1 hour soft limit
    task_time_limit=3900,  # 1 hour 5 min hard limit
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (memory cleanup)
    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours
    result_extended=True,  # Store additional task metadata
    # Retry settings
    task_default_retry_delay=60,  # 1 minute default retry delay
    task_max_retries=3,  # Maximum 3 retries
    # Queue routing with priorities
    task_default_queue="agents",  # Default queue for agent tasks
    task_routes={
        "service.infrastructure.messaging.tasks.process_agent_message": {
            "queue": "agents",
            "priority": 5,  # High priority for agent messages
        },
        "service.infrastructure.messaging.tasks.cleanup_old_streams": {
            "queue": "maintenance",
            "priority": 1,  # Low priority for cleanup tasks
        },
        "service.infrastructure.messaging.tasks.delete_old_chat_history": {
            "queue": "maintenance",
            "priority": 1,  # Low priority for cleanup tasks
        },
    },
    # Define queues with priority support
    task_queues={
        "agents": {
            "exchange": "agents",
            "routing_key": "agents",
            "queue_arguments": {"x-max-priority": 10},  # Support priorities 0-10
        },
        "maintenance": {
            "exchange": "maintenance",
            "routing_key": "maintenance",
            "queue_arguments": {"x-max-priority": 5},  # Lower priority range for maintenance
        },
    },
)

# Beat schedule for periodic tasks (if needed)
celery_app.conf.beat_schedule = {
    # Clean up old chat messages once per day by default (configurable via env)
    "cleanup-old-chat-history": {
        "task": "service.infrastructure.messaging.tasks.delete_old_chat_history",
        "schedule": float(os.getenv("CHAT_RETENTION_SCHEDULE_SECONDS", str(24 * 3600))),
    },
    # Clean up old Redis Streams every hour
    "cleanup-old-streams": {
        "task": "service.infrastructure.messaging.tasks.cleanup_old_streams",
        "schedule": 3600.0,  # Every hour
    },
}

logger.info("Celery app configured with broker: %s", CELERY_BROKER_URL)
