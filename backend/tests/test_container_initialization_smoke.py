import pytest


def test_build_container_smoke_required_dependencies() -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("sqlalchemy")

    from service.composition.container import build_container
    from service.composition.models import AppContainer
    from service.settings import Config

    app_container = build_container(Config())

    assert isinstance(app_container, AppContainer)
    assert app_container.infra.background_task_manager is not None
    assert app_container.infra.pg_connector is not None
    assert app_container.infra.stream_port is not None
    assert app_container.infra.message_bus_port is not None
    assert app_container.infra.job_queue_port is not None
    assert app_container.repositories.auth_repository is not None
    assert app_container.repositories.job_repository is not None
    assert app_container.repositories.profile_repository is not None
    assert app_container.repositories.file_repository is not None
    assert app_container.services.auth_service is not None
    assert app_container.services.job_service is not None
    assert app_container.services.profile_service is not None
    assert app_container.services.file_saver_service is not None
    assert app_container.services.process_chat_message_handler is not None
    assert app_container.services.new_job_processor is not None


def test_create_app_accepts_container_override() -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("sqlalchemy")

    from service.composition.container import build_container
    from service.main import create_app
    from service.settings import Config

    app_container = build_container(Config())
    app = create_app(container_override=app_container)

    assert app.state.container is app_container
