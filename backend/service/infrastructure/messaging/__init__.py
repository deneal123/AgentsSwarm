"""Celery messaging infrastructure package."""

from service.infrastructure.messaging.celery_app import celery_app

__all__ = [
    "celery_app"
]
