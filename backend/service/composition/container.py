from __future__ import annotations

from service.composition.infra import build_infra
from service.composition.models import AppContainer
from service.composition.repositories import build_repositories
from service.composition.services import build_services
from service.settings import Config


def build_container(config: Config) -> AppContainer:
    infra = build_infra(config)
    repositories = build_repositories(infra)
    services = build_services(repositories, infra, config)
    return AppContainer(infra=infra, repositories=repositories, services=services)
