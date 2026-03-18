"""Celery application configuration for Pushi platform.

Provides unified task routing for all background operations:
- Playground (single/batch communication analysis)
- Pipeline (dataset analysis)
- File uploads (configs, datasets)
- Maintenance (cleanup, health checks)
"""

import os
from pathlib import Path

from celery import Celery

# Celery configuration
broker_url = os.getenv("CELERY__BROKER_URL", "amqp://guest:guest@rabbitmq:5672//")
result_backend = os.getenv("CELERY__RESULT_BACKEND")

redis_host = os.getenv("REDIS__HOST", "redis")
redis_port = os.getenv("REDIS__PORT", "6379")
redis_pass = os.getenv("REDIS__PASSWORD", "")
redis_db = os.getenv("REDIS__RESULT_DB", "1")

# If result_backend is provided in ENV, but doesn't have credentials while Redis has them,
# or if it's not provided at all, we re-construct it.
if not result_backend or (redis_pass and f"redis://{redis_host}" in result_backend and "@" not in result_backend):
    if redis_pass:
        result_backend = f"redis://:{redis_pass}@{redis_host}:{redis_port}/{redis_db}"
    else:
        result_backend = f"redis://{redis_host}:{redis_port}/{redis_db}"

# Create Celery app
celery_app = Celery(
    "pushi_tasks",
    broker=broker_url,
    backend=result_backend,
    include=[
        # Task modules - automatically discover tasks
        "service.infrastructure.messaging.tasks.playground_tasks",
        "service.infrastructure.messaging.tasks.pipeline_tasks",
        "service.infrastructure.messaging.tasks.file_tasks",
        "service.infrastructure.messaging.tasks.maintenance_tasks",
    ],
)

# ============================================================================
# Task Routing Configuration
# ============================================================================

celery_app.conf.task_routes = {
    # Playground tasks
    "service.infrastructure.messaging.tasks.playground_tasks.process_playground_single": {
        "queue": "playground",
        "routing_key": "playground.single",
    },
    "service.infrastructure.messaging.tasks.playground_tasks.process_playground_batch": {
        "queue": "playground",
        "routing_key": "playground.batch",
    },
    # Pipeline tasks
    "service.infrastructure.messaging.tasks.pipeline_tasks.process_pipeline": {
        "queue": "pipeline",
        "routing_key": "pipeline.process",
    },
    # File tasks
    "service.infrastructure.messaging.tasks.file_tasks.process_config_upload": {
        "queue": "maintenance",
        "routing_key": "file.config",
    },
    "service.infrastructure.messaging.tasks.file_tasks.process_dataset_upload": {
        "queue": "maintenance",
        "routing_key": "file.dataset",
    },
    "service.infrastructure.messaging.tasks.file_tasks.process_rule_config": {
        "queue": "maintenance",
        "routing_key": "file.rule_config",
    },
    # Maintenance tasks
    "service.infrastructure.messaging.tasks.maintenance_tasks.cleanup_old_tasks": {
        "queue": "maintenance",
        "routing_key": "maintenance.cleanup.tasks",
    },
    "service.infrastructure.messaging.tasks.maintenance_tasks.cleanup_expired_sessions": {
        "queue": "maintenance",
        "routing_key": "maintenance.cleanup.sessions",
    },
    "service.infrastructure.messaging.tasks.maintenance_tasks.cleanup_completed_queue_entries": {
        "queue": "maintenance",
        "routing_key": "maintenance.cleanup.queue",
    },
    "service.infrastructure.messaging.tasks.maintenance_tasks.archive_old_files": {
        "queue": "maintenance",
        "routing_key": "maintenance.cleanup.files",
    },
    "service.infrastructure.messaging.tasks.maintenance_tasks.cleanup_old_streams": {
        "queue": "maintenance",
        "routing_key": "maintenance.cleanup.streams",
    },
}

# ============================================================================
# Task Default Configuration
# ============================================================================

celery_app.conf.update(
    # Task execution
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task tracking
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max execution
    task_soft_time_limit=3300,  # 55 min soft limit
    
    # Result backend
    result_expires=86400,  # 24 hours
    result_extended=True,
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Retry configuration
    task_default_retry_delay=60,
    task_max_retries=3,
)

# ============================================================================
# Queue Configuration
# ============================================================================

celery_app.conf.task_default_queue = "default"
celery_app.conf.task_queues = {
    "default": {
        "exchange": "default",
        "exchange_type": "direct",
        "routing_key": "default",
    },
    # Playground queue - communication analysis
    # Actual thread allocation controlled by TaskOrchestratorService
    # based on max_parallel_batches from task config (up to max_project_threads)
    "playground": {
        "exchange": "playground",
        "exchange_type": "direct",
        "routing_key": "playground.#",
    },
    # Pipeline queue - dataset analysis
    # Actual thread allocation controlled by TaskOrchestratorService
    # based on max_parallel_batches from task config (up to max_project_threads)
    "pipeline": {
        "exchange": "pipeline",
        "exchange_type": "direct",
        "routing_key": "pipeline.#",
    },
    # Maintenance queue - cleanup and file processing
    "maintenance": {
        "exchange": "maintenance",
        "exchange_type": "direct",
        "routing_key": "maintenance.#",
    },
}

# ============================================================================
# Beat Schedule (Periodic Tasks)
# ============================================================================
# NOTE: Beat schedule is configured in beat_schedule.py and applied in
# app/__init__.py — do NOT define it here to avoid duplication.

# ============================================================================
# Auto-discovery
# ============================================================================

# Automatically discover tasks from installed apps
celery_app.autodiscover_tasks()


def get_celery_app() -> Celery:
    """Get configured Celery application instance."""
    return celery_app