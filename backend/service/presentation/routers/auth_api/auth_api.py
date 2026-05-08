import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Response

from service.presentation.dependencies import providers
from service.presentation.routers.auth_api.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)
from service.services.profile.application.auth_service import AuthService
from service.settings import config

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/api/auth/v1")


@auth_router.post(
    path="/register",
    response_model=RegisterResponse,
    summary="User registration with password",
    description="Register new user with email and password. User needs to login separately after registration.",
)
async def register(
    request_body: Annotated[RegisterRequest, Body],
    request: Request,
    service: Annotated[AuthService, Depends(providers.get_auth_service)],
) -> RegisterResponse:

    user_agent = request.headers.get("user-agent", "unknown")
    register_result = await service.register_user(user_agent, request_body)

    return register_result


@auth_router.post(
    path="/login",
    response_model=LoginResponse,
    summary="User login with password",
    description="Login with email and password. Returns JWT token on success.",
)
async def login(
    request_body: Annotated[LoginRequest, Body],
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(providers.get_auth_service)],
) -> LoginResponse:

    user_agent = request.headers.get("user-agent", "unknown")
    user_jwt = await service.login(user_agent, request_body)

    # Hardened cookie settings (production-ready):
    # - secure=True (requires HTTPS; keep False only in explicit dev override)
    # - samesite='strict' to mitigate CSRF; adjust to 'lax' if third‑party contexts needed
    secure_cookie = not config.auth.dev_mode
    response.set_cookie(
        key="auth_token",
        value=user_jwt.jwt,
        httponly=True,
        secure=secure_cookie,
        samesite="strict" if secure_cookie else "lax",
        max_age=int(config.auth.jwt_exp_hours * 3600),
        path="/",
    )

    return user_jwt
