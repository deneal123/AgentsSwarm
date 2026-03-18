"""CORS middleware configuration."""

from typing import List

from fastapi.middleware.cors import CORSMiddleware


def create_cors_middleware(
    allow_origins: List[str],
    allow_credentials: bool = True,
    allow_methods: List[str] = None,
    allow_headers: List[str] = None,
) -> CORSMiddleware:
    """Create CORS middleware with configurable settings."""
    if allow_methods is None:
        allow_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

    if allow_headers is None:
        allow_headers = ["*"]

    # Return a partial middleware that can be added to app
    class ConfigurableCORSMiddleware(CORSMiddleware):
        def __init__(self, app):
            super().__init__(
                app=app,
                allow_origins=allow_origins,
                allow_credentials=allow_credentials,
                allow_methods=allow_methods,
                allow_headers=allow_headers,
            )

    return ConfigurableCORSMiddleware
