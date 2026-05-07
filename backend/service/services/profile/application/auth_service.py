import logging
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status

from service.models.db.db_models import UserSession
from service.models.key_value import SessionStatus, UserTypes
from service.models.profile_models import UserProfileLogic
from service.presentation.routers.auth_api.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)
from service.repositories.auth_repository import AuthRepository
from service.services.profile.application.profile_service import ProfileService
from service.settings import AuthConfig

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(
        self,
        config: AuthConfig,
        repository: AuthRepository,
        profile_source: ProfileService,
    ) -> None:
        self.config = config
        self.repository = repository
        self.profile_source = profile_source

    async def register_user(
        self, user_agent: str, request_body: RegisterRequest
    ) -> RegisterResponse:
        """Register new user with email and password"""

        normalized_email = self._normalize_email(request_body.email)

        # Basic password strength policy: >=8 chars, contains letter and digit
        pwd = request_body.password or ""
        if len(pwd) < 8 or not any(c.isalpha() for c in pwd) or not any(c.isdigit() for c in pwd):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long and contain letters and digits",
            )

        # Check if user already exists
        existing_user = await self.profile_source.fetch_user_profile_by_email(normalized_email)
        if existing_user:
            logger.warning(f"User already exists: {normalized_email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists",
            )

        # Create new user with hashed password
        user = await self.profile_source.create_new_user(
            email=normalized_email, password=request_body.password
        )
        logger.info(f"Created new user: {user.id} with email: {user.email}")

        response = RegisterResponse(
            email=user.email,
            user_id=user.id,
        )

        return response

    async def login(self, user_agent: str, request_body: LoginRequest) -> LoginResponse:
        """Login user with email and password"""

        normalized_email = self._normalize_email(request_body.email)

        user = await self.profile_source.fetch_user_profile_by_email(normalized_email)
        if not user:
            logger.warning(f"Login attempt for non-existent user: {normalized_email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or password"
            )

        # Verify password
        if not self.profile_source.verify_password(request_body.password, user.password_hash):
            logger.warning(f"Invalid password for user: {normalized_email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or password"
            )

        logger.info(f"User {user.email} logged in successfully")

        # Create activated session
        session = await self._create_activated_session(
            user=user,
            user_agent=user_agent,
            fingerprint=None,
        )

        logger.info(f"Created session: {session.id} for user: {user.id}")

        response = LoginResponse(
            jwt=session.token,  # type: ignore
        )

        return response

    async def _create_activated_session(
        self,
        user: UserProfileLogic,
        user_agent: str,
        fingerprint: str | None,
    ) -> UserSession:
        """Create an immediately activated session"""

        jwt_token = self._create_jwt(user.id, fingerprint, UserTypes.REGISTERED)

        new_session = UserSession(
            user_id=user.id,
            user_agent=user_agent,
            fingerprint=fingerprint,
            status=SessionStatus.ACTIVATED,
            session_code="",  # No code needed for password auth
            token=jwt_token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=self.config.jwt_exp_hours),
        )
        return await self.repository.create_session(new_session)

    def _create_jwt(self, user_id, fingerprint: str | None, user_type: UserTypes) -> str:
        """Create JWT token for authenticated user"""

        payload = {
            "sub": str(user_id),
            "fingerprint": fingerprint,
            "type": user_type.value,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=self.config.jwt_exp_hours),
        }
        token = jwt.encode(payload, self.config.secret, algorithm=self.config.algorithm)
        return token

    def _normalize_email(self, email: str) -> str:
        """Normalize email address"""
        local_part, domain_part = email.rsplit("@", 1)

        if "+" in local_part:
            local_part = local_part.split("+")[0]

        return f"{local_part}@{domain_part}".lower()
