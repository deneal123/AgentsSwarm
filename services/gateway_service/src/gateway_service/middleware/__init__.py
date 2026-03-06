"""Gateway Service — HTTP middleware."""

from gateway_service.middleware.logging import RequestLoggingMiddleware

__all__ = ["RequestLoggingMiddleware"]
