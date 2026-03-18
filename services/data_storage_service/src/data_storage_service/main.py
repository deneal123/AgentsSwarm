import logging
import logging.config

import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from service.container import RedisClientName

from service.presentation.api_tags import API_TAGS
from service.presentation.handlers.exceptions_handlers import setup_exception_handlers
from service.presentation.middleware import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    TimingMiddleware,
    create_cors_middleware,
)
from service.presentation.routers.v1 import (
    auth_router,
    communication_results_router,
    file_uploads_router,
    pipeline_router,
    playground_router,
    profile_router,
    rules_router,
)
from service.presentation.routers.ws import (
    tasks_ws_router,
)
from service.settings import LOGGING, config
from service.utils.app_lifespan import health_check, lifespan

logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)
logger.info(f"config.initialized: {config.model_dump_json(indent=4)}")

def create_app() -> FastAPI:

    # Точка входа в приложение
    app = FastAPI(
        title=f"{config.fastapi_app.service_name} API",
        description=f"{config.fastapi_app.description}",
        version=f"{config.fastapi_app.version}",
        lifespan=lifespan,
        docs_url=f"{config.fastapi_app.docs_url}",
        openapi_url=f"{config.fastapi_app.openapi_url}",
        redoc_url=f"{config.fastapi_app.redoc_url}",
        openapi_tags=API_TAGS,
    )

    # Настройка middleware
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(TimingMiddleware)

    # Rate limiting: pass a lazy getter so Redis is resolved after container.build()
    from service.container import getter as container_getter
    app.add_middleware(
        RateLimitMiddleware,
        redis_getter=container_getter(RedisClientName),
        requests_per_minute=config.rate_limit.requests_per_minute,
        burst_limit=config.rate_limit.burst_limit,
    )
    logger.info("Rate limiting middleware registered (Redis resolved lazily)")

    # CORS middleware
    cors_config = getattr(config, "cors", None)
    allow_origins = getattr(cors_config, "allow_origins", []) if cors_config else []
    if allow_origins:
        cors_middleware_class = create_cors_middleware(allow_origins)
        app.add_middleware(cors_middleware_class)
    else:
        cors_middleware_class = create_cors_middleware(
            [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
            ]
        )
        app.add_middleware(cors_middleware_class)

    # Core API routers (v1)
    app.include_router(auth_router)
    app.include_router(profile_router)

    # Pushi-specific routers
    app.include_router(rules_router)

    # New unified task routers
    app.include_router(playground_router)
    app.include_router(pipeline_router)
    app.include_router(file_uploads_router)
    app.include_router(communication_results_router)

    # WebSocket routers
    app.include_router(tasks_ws_router, tags=["Tasks-WebSocket"])

    setup_exception_handlers(app)

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        root_payload = {
            "title": f"{config.fastapi_app.service_name} API",
            "description": config.fastapi_app.description,
            "version": config.fastapi_app.version,
            "docs": config.fastapi_app.docs_url,
            "openapi": config.fastapi_app.openapi_url,
            "redoc": config.fastapi_app.redoc_url,
        }
        return root_payload

    @app.get("/api/health", include_in_schema=False)
    async def health() -> dict:
        """Comprehensive health check endpoint.

        Returns:
            Health status including:
            - System components (database, redis, etc.)
            - Overall health status
        """
        return await health_check()

    return app


app = create_app()
