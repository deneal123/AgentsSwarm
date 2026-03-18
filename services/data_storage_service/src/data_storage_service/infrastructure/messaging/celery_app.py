"""Celery app entrypoints for backwards compatibility."""

from service.infrastructure.messaging.app.celery_app import celery_app

__all__ = ["celery_app"]
