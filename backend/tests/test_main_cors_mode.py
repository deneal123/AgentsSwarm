from __future__ import annotations

import pytest

pytest.importorskip("fastapi.middleware.cors")
from fastapi.middleware.cors import CORSMiddleware


def _cors_middleware_options(app) -> dict | None:
    for middleware in app.user_middleware:
        if middleware.cls is CORSMiddleware:
            return dict(middleware.kwargs)
    return None


def test_create_app_uses_localhost_fallback_in_dev_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    from service import main as service_main

    monkeypatch.setattr(service_main.config.auth, "auth_mode", "dev")
    monkeypatch.setattr(service_main.config.cors, "allow_origins", [])

    app = service_main.create_app()
    cors_options = _cors_middleware_options(app)

    assert cors_options is not None
    assert cors_options["allow_origins"] == [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]


def test_create_app_fails_fast_without_cors_origins_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    from service import main as service_main

    monkeypatch.setattr(service_main.config.auth, "auth_mode", "prod")
    monkeypatch.setattr(service_main.config.cors, "allow_origins", [])

    with pytest.raises(RuntimeError, match="CORS_ALLOW_ORIGINS must be configured in production mode"):
        service_main.create_app()
