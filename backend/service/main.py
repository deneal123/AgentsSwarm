import logging
import logging.config

from fastapi import FastAPI

from service.container import AppContainer
from fastapi.middleware.cors import CORSMiddleware

from service.presentation.handlers.exceptions_handlers import setup_exception_handlers
from service.presentation.routers.auth_api.auth_api import auth_router
from service.presentation.routers.files_api.files_api import files_router
from service.presentation.routers.jobs_api.jobs_api import jobs_router
from service.presentation.routers.profile_api.profile_api import profile_router
from service.services.chat.presentation.routers.chat_api.chat_api import chat_router
from service.presentation.routers.memory_api.memory_api import memory_router
from service.presentation.routers.analytics_api.analytics_api import analytics_router
from service.services.chat.presentation.routers.chat_ws import router as chat_ws_router
from service.presentation.routers.jobs_ws import router as jobs_ws_router
from service.presentation.routers.debug_api import router as debug_router
from service.settings import LOGGING, config
from service.utils.app_lifespan import lifespan

logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)
logger.info(f"config.initialized: {config.model_dump_json(indent=4)}")


def create_app(container_override: AppContainer | None = None) -> FastAPI:
    service_title = (getattr(config.service, "name", "") or "").strip() or "GPTHub API"
    app = FastAPI(
        title=service_title,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url="/api/redoc",
    )


    if container_override is not None:
        app.state.container = container_override

    # CORS middleware for WebSocket support
    cors_config = getattr(config, "cors", None)
    allow_origins = getattr(cors_config, "allow_origins", []) if cors_config else []
    if allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        # Fallback for development
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(auth_router, tags=["Auth-API"])
    app.include_router(jobs_router, tags=["Jobs-API"])
    app.include_router(files_router, tags=["Files-API"])
    app.include_router(profile_router, tags=["Profile-API"])
    app.include_router(chat_ws_router, tags=["Chat-WS"])
    app.include_router(jobs_ws_router, tags=["Jobs-WS"])
    app.include_router(debug_router, tags=["Debug"])
    app.include_router(chat_router, tags=["Chat-API"])
    app.include_router(memory_router, tags=["Memory-API"])
    app.include_router(analytics_router, tags=["Analytics-API"])

    setup_exception_handlers(app)

    @app.get("/api/health", include_in_schema=False)
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
