"""Request timing middleware."""

import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to measure and log request timing."""

    def __init__(self, app, slow_request_threshold: float = 1.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold

    async def dispatch(self, request: Request, call_next):
        """Measure request execution time."""
        start_time = time.time()

        try:
            response = await call_next(request)

            # Get request ID after all middleware has processed the request
            request_id = getattr(request.state, "request_id", "unknown")

            # Calculate duration
            duration = time.time() - start_time
            duration_ms = duration * 1000

            # Add timing header to response
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            # Log slow requests
            if duration >= self.slow_request_threshold:
                logger.warning(
                    f"Slow request: {request.method} {request.url.path} "
                    f"took {duration_ms:.2f}ms (request_id: {request_id})"
                )
            else:
                logger.debug(
                    f"Request completed: {request.method} {request.url.path} "
                    f"in {duration_ms:.2f}ms (request_id: {request_id})"
                )

            return response

        except Exception as e:
            # Get request ID even in exception case
            request_id = getattr(request.state, "request_id", "unknown")
            
            # Log exceptions with timing
            duration = time.time() - start_time
            duration_ms = duration * 1000

            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"after {duration_ms:.2f}ms (request_id: {request_id}) - {e}"
            )
            raise
