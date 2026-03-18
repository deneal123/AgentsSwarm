"""REST API v1 routers."""

from .auth import auth_router
from .communication_results import communication_results_router
from .file_uploads import file_uploads_router
from .pipeline import pipeline_router
from .playground import playground_router
from .profile import profile_router
from .rules import rules_router

__all__ = [
    "auth_router",
    "profile_router",
    "file_uploads_router",
    "rules_router",
    "playground_router",
    "pipeline_router",
    "communication_results_router",
]
