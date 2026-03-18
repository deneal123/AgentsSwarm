"""Request ID middleware for tracing."""

import uuid
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID for tracing."""

    def __init__(self, app, header_name: str = "X-Request-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        """Add request ID to request and response."""
        # Get or generate request ID
        request_id = self._get_or_generate_request_id(request)

        # Add to request state for use in handlers
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers[self.header_name] = request_id

        return response

    def _get_or_generate_request_id(self, request: Request) -> str:
        """Get request ID from header or generate new one."""
        existing_id = request.headers.get(self.header_name)
        if existing_id and self._is_valid_uuid(existing_id):
            return existing_id
        return str(uuid.uuid4())

    def _is_valid_uuid(self, value: str) -> bool:
        """Check if string is a valid UUID."""
        try:
            uuid.UUID(value)
            return True
        except ValueError:
            return False
