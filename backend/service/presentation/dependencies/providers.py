from __future__ import annotations

from typing import Any

from fastapi import Request

from service.composition.models import AppContainer
from service.composition.state import get_current_container
from service.services.files.application.file_saver_service import FileSaverService
from service.services.jobs.application.job_service import JobService
from service.services.profile.application.auth_service import AuthService
from service.services.profile.application.profile_service import ProfileService


def get_app_container(request: Request) -> AppContainer:
    app_container = getattr(request.app.state, "container", None)
    if app_container is not None:
        return app_container
    return get_current_container()


def get_auth_service(request: Request) -> AuthService:
    return get_app_container(request).services.auth_service


def get_job_service(request: Request) -> JobService:
    return get_app_container(request).services.job_service


def get_profile_service(request: Request) -> ProfileService:
    return get_app_container(request).services.profile_service


def get_file_saver_service(request: Request) -> FileSaverService:
    return get_app_container(request).services.file_saver_service


def get_optional_redis_client(request: Request) -> Any:
    return get_app_container(request).infra.redis_client


def get_optional_redis_session_store(request: Request) -> Any:
    return get_app_container(request).infra.redis_session_store


def get_chat_application_service(request: Request) -> Any:
    return get_app_container(request).services.chat_application_service


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
