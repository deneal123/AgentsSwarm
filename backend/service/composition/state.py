from __future__ import annotations

from typing import Any

from starlette.requests import HTTPConnection

from service.composition.models import AppContainer
from service.services.analytics.application.analytics_service import AnalyticsService
from service.services.files.application.file_saver_service import FileSaverService
from service.services.jobs.application.job_service import JobService
from service.services.profile.application.auth_service import AuthService
from service.services.profile.application.profile_service import ProfileService

_CURRENT_CONTAINER: AppContainer | None = None


def set_current_container(app_container: AppContainer) -> None:
    global _CURRENT_CONTAINER
    _CURRENT_CONTAINER = app_container


def get_current_container() -> AppContainer:
    if _CURRENT_CONTAINER is None:
        raise RuntimeError("Dependency container not initialized")
    return _CURRENT_CONTAINER


def get_app_container(request: HTTPConnection) -> AppContainer:
    app_container = getattr(request.app.state, "container", None)
    if app_container is not None:
        return app_container
    return get_current_container()


def get_auth_service(request: HTTPConnection) -> AuthService:
    return get_app_container(request).services.auth_service


def get_job_service(request: HTTPConnection) -> JobService:
    return get_app_container(request).services.job_service


def get_profile_service(request: HTTPConnection) -> ProfileService:
    return get_app_container(request).services.profile_service


def get_file_saver_service(request: HTTPConnection) -> FileSaverService:
    return get_app_container(request).services.file_saver_service


def get_analytics_service(request: HTTPConnection) -> AnalyticsService:
    return get_app_container(request).services.analytics_service


def get_optional_redis_client(request: HTTPConnection) -> Any:
    return get_app_container(request).infra.redis_client


def get_optional_redis_session_store(request: HTTPConnection) -> Any:
    return get_app_container(request).infra.redis_session_store


def get_chat_application_service(request: HTTPConnection) -> Any:
    return get_app_container(request).services.chat_application_service
