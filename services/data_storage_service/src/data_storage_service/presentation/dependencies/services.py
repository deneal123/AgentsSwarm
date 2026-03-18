"""Dependency injection helpers for FastAPI."""

from typing import Any, Callable

from service.container import (
    AuthServiceName,
    CeleryAppName,
    CommunicationResultServiceName,
    FileLogicName,
    FileSaverServiceName,
    PipelineLogicName,
    PlaygroundLogicName,
    PlaygroundServiceName,
    PipelineServiceName,
    ProfileServiceName,
    RuleServiceName,
    TaskServiceName,
    get,
)


def _build_dependency(name: str) -> Callable[[], Any]:
    def dependency() -> Any:
        return get(name)

    dependency.__name__ = f"_resolve_{name.lower()}"
    return dependency


# Auth services
get_auth_service = _build_dependency(AuthServiceName)
get_profile_service = _build_dependency(ProfileServiceName)

# File services
get_file_saver_service = _build_dependency(FileSaverServiceName)

# Task services
get_task_service = _build_dependency(TaskServiceName)

# Pushi services
get_rule_service = _build_dependency(RuleServiceName)
get_playground_service = _build_dependency(PlaygroundServiceName)
get_pipeline_service = _build_dependency(PipelineServiceName)

# Logic layer
get_playground_logic = _build_dependency(PlaygroundLogicName)
get_pipeline_logic = _build_dependency(PipelineLogicName)
get_file_logic = _build_dependency(FileLogicName)

# Celery app
get_celery_app = _build_dependency(CeleryAppName)

# Communication results
get_communication_result_service = _build_dependency(CommunicationResultServiceName)
