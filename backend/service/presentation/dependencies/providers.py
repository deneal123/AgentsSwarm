"""Presentation-layer dependency providers.

All implementations live in `service.composition.state`; this module
re-exports them so presentation code uses a stable, self-contained import path.
"""

from service.composition.state import (
    get_app_container,
    get_auth_service,
    get_chat_application_service,
    get_file_saver_service,
    get_job_service,
    get_optional_redis_client,
    get_optional_redis_session_store,
    get_profile_service,
)

__all__ = [
    "get_app_container",
    "get_auth_service",
    "get_job_service",
    "get_profile_service",
    "get_file_saver_service",
    "get_optional_redis_client",
    "get_optional_redis_session_store",
    "get_chat_application_service",
]
