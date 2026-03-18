from service.infrastructure.messaging.app.beat_schedule import beat_schedule
from service.infrastructure.messaging.app.celery_app import celery_app

celery_app.conf.beat_schedule = beat_schedule

__all__ = ["celery_app", "beat_schedule"]
