"""Celery Beat schedule for Pushi periodic tasks."""

from celery.schedules import crontab

beat_schedule = {
    # Удаление старых задач ежедневно в 3:00
    "cleanup-old-tasks": {
        "task": "service.infrastructure.messaging.tasks.maintenance_tasks.cleanup_old_tasks",
        "schedule": crontab(hour=3, minute=0),
        "args": (30,),  # хранить последние 30 дней
        "options": {"queue": "maintenance", "priority": 1},
    },
    # Удаление истёкших гостевых сессий каждый час в :15
    "cleanup-expired-sessions": {
        "task": "service.infrastructure.messaging.tasks.maintenance_tasks.cleanup_expired_sessions",
        "schedule": crontab(minute=15),
        "options": {"queue": "maintenance", "priority": 2},
    },
    # Удаление завершённых записей очереди pipeline ежедневно в 2:00
    "cleanup-completed-queue": {
        "task": "service.infrastructure.messaging.tasks.maintenance_tasks.cleanup_completed_queue_entries",
        "schedule": crontab(hour=2, minute=0),
        "args": (7,),  # хранить последние 7 дней
        "options": {"queue": "maintenance", "priority": 2},
    },
    # Удаление старых файлов каждое воскресенье в 4:00
    "cleanup-old-files": {
        "task": "service.infrastructure.messaging.tasks.maintenance_tasks.archive_old_files",
        "schedule": crontab(hour=4, minute=0, day_of_week=0),
        "args": (90,),  # хранить последние 90 дней
        "options": {"queue": "maintenance", "priority": 1},
    },
    # Очистка устаревших ключей Redis каждый час
    "cleanup-old-streams": {
        "task": "service.infrastructure.messaging.tasks.maintenance_tasks.cleanup_old_streams",
        "schedule": crontab(minute=0),
        "options": {"queue": "maintenance", "priority": 1},
    },
}
