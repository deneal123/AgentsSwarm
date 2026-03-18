"""Dependencies for FastAPI routes."""

from .auth import get_current_user, get_current_user_optional, require_admin, require_user
from .pagination import PaginationParams
from .services import (
    get_auth_service,
    get_profile_service,
    get_file_saver_service,
    get_task_service,
    get_rule_service,
    get_playground_service,
    get_pipeline_service,
    get_celery_app,
)
from .ws_auth import authenticate_websocket

__all__ = [
    # Auth dependencies
    "get_current_user",
    "get_current_user_optional",
    "require_admin",
    "require_user",
    # WebSocket auth
    "authenticate_websocket",
    # Pagination
    "PaginationParams",
    # Core services
    "get_auth_service",
    "get_profile_service",
    "get_file_saver_service",
    "get_task_service",
    # Pushi services
    "get_rule_service",
    "get_playground_service",
    "get_pipeline_service",
    # Pushi orchestrator
    # (orchestrator provided via container if needed)
    # Celery
    "get_celery_app",
]
