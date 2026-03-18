import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from fastapi import HTTPException, status
from service.models.db.session_models import UserSession
from service.models.enums import SessionStatus, UserRole, UserType
from service.models.pydantic.auth import (
    LoginRequest,
    LoginResponse,
    RegisterResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
)
from service.models.pydantic.profile import UserCreate, UserResponse
from service.models.pydantic.session import UserSessionResponse
from service.repositories.auth_repository import AuthRepository
from service.services.base_service import BaseService
from service.services.profile_service import ProfileService
from service.utils.logging_decorators import log_operation
from service.settings import AuthConfig


class AuthService(BaseService[AuthRepository]):
    """Service for authentication and session management."""

    def __init__(
        self,
        config: AuthConfig,
        repository: AuthRepository,
        profile_service: ProfileService,
    ) -> None:
        super().__init__(repository)
        self.config = config
        self.profile_service = profile_service
        self._login_attempts: dict[str, dict[str, Any]] = {}

    @property
    def repository(self) -> AuthRepository:
        """Typed alias for the underlying AuthRepository (keeps usage consistent)."""
        return self.repo

    @staticmethod
    def validate_password_strength(password: str) -> None:
        """Validate password strength.

        Args:
            password: Password to validate

        Raises:
            HTTPException: If password doesn't meet requirements
        """
        if len(password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long",
            )
        if not any(c.isalpha() for c in password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must contain at least one letter",
            )
        if not any(c.isdigit() for c in password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must contain at least one digit",
            )

    @log_operation(log_args=True)
    async def register_user(self, user_agent: str, request_body: UserCreate) -> RegisterResponse:
        """Register new user with email and password.

        Args:
            user_agent: User agent string
            request_body: Registration request data

        Returns:
            RegisterResponse with created user info

        Raises:
            HTTPException: If user already exists or validation fails
        """
        normalized_email = ProfileService.normalize_email(request_body.email)

        self.validate_password_strength(request_body.password)

        existing_user = await self.profile_service.fetch_user_profile_by_email(normalized_email)
        if existing_user:
            self.logger.warning(f"User already exists: {normalized_email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists",
            )

        user = await self.profile_service.create_new_user(
            email=normalized_email, password=request_body.password
        )

        session = await self._create_activated_session(
            user_id=user.id,
            user_agent=user_agent,
            fingerprint=None,
            user_role=self._resolve_user_role(user.role),
        )

        return RegisterResponse(
            user=user,
            access_token=session.token,
            refresh_token=session.refresh_token or "",
        )

    @log_operation(log_args=True)
    async def login(self, user_agent: str, request_body: LoginRequest) -> LoginResponse:
        """Login user with email and password.

        Args:
            user_agent: User agent string
            request_body: Login request data

        Returns:
            LoginResponse with JWT token and user info

        Raises:
            HTTPException: If credentials are invalid
        """
        try:
            normalized_email = ProfileService.normalize_email(request_body.email)
        except ValueError:
            normalized_email = request_body.email.strip().lower()
        self._ensure_account_not_locked(normalized_email)

        user = await self.profile_service.fetch_user_profile_by_email(normalized_email)
        if not user:
            self._record_failed_attempt(normalized_email)
            self.logger.warning(f"Login attempt for non-existent user: {normalized_email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or password"
            )

        user_with_password = await self.profile_service.fetch_user_with_credentials(
            normalized_email
        )
        if not user_with_password:
            self._record_failed_attempt(normalized_email)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or password"
            )

        if not ProfileService.verify_password(
            request_body.password, user_with_password.password_hash
        ):
            self._record_failed_attempt(normalized_email)
            self.logger.warning(f"Invalid password for user: {normalized_email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or password"
            )

        self._reset_login_attempts(normalized_email)

        session = await self._create_activated_session(
            user_id=user.id,
            user_agent=user_agent,
            fingerprint=request_body.fingerprint,
            user_role=self._resolve_user_role(user.role),
        )

        self._log_operation("create_session", "Session", session.id)

        return LoginResponse(
            access_token=session.token,
            refresh_token=session.refresh_token or "",
            user=user,
        )

    async def _create_activated_session(
        self,
        user_id: UUID,
        user_agent: str,
        fingerprint: str | None,
        user_role: UserRole,
    ) -> UserSession:
        """Create an immediately activated session.

        Args:
            user_id: User UUID
            user_agent: User agent string
            fingerprint: Optional device fingerprint

        Returns:
            UserSession object
        """
        jwt_token = self._create_jwt(user_id, fingerprint, user_role)
        refresh_token = self._generate_refresh_token()

        new_session = UserSession(
            user_id=user_id,
            user_agent=user_agent,
            fingerprint=fingerprint,
            status=SessionStatus.ACTIVE,
            token=jwt_token,
            refresh_token=refresh_token,
            expires_at=self._get_session_expiration(),
        )
        return await self.repository.create_session(new_session)

    def _create_jwt(self, user_id: UUID, fingerprint: str | None, user_role: UserRole) -> str:
        """Create JWT token for authenticated user.

        Args:
            user_id: User UUID
            fingerprint: Optional device fingerprint
            user_role: User role

        Returns:
            JWT token string
        """
        payload = {
            "sub": str(user_id),
            "fingerprint": fingerprint,
            "role": user_role.value,
            "type": UserType.REGISTERED_USER.value,
            "iat": self._get_current_time(),
            "exp": self._get_session_expiration(),
        }
        token = jwt.encode(payload, self.config.secret, algorithm=self.config.algorithm)
        return token

    def _get_current_time(self) -> datetime:
        return datetime.now(timezone.utc)

    def _get_session_expiration(self) -> datetime:
        return self._get_current_time() + timedelta(hours=self.config.jwt_exp_hours)

    def _generate_refresh_token(self) -> str:
        return secrets.token_urlsafe(48)

    def _ensure_account_not_locked(self, email: str) -> None:
        record = self._login_attempts.get(email)
        if not record:
            return

        locked_until = record.get("locked_until")
        if locked_until and locked_until > self._get_current_time():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked until {locked_until.isoformat()}",
            )

    def _record_failed_attempt(self, email: str) -> None:
        record = self._login_attempts.setdefault(email, {"count": 0, "locked_until": None})
        record["count"] += 1

        if record["count"] >= self.config.max_login_attempts:
            record["locked_until"] = self._get_current_time() + timedelta(
                minutes=self.config.lockout_minutes
            )

    def _reset_login_attempts(self, email: str) -> None:
        self._login_attempts.pop(email, None)

    def _resolve_user_role(self, role: str | None) -> UserRole:
        if not role:
            return UserRole.LAWYER
        try:
            return UserRole(role)
        except ValueError:
            return UserRole.LAWYER

    def _decode_jwt(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(
                token,
                self.config.secret,
                algorithms=[self.config.algorithm],
                options={"verify_aud": False},
            )
        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
            ) from exc
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            ) from exc

    async def _refresh_session_tokens(self, session: UserSession) -> UserSession:
        profile = await self.profile_service.fetch_user_profile(session.user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found"
            )

        session.token = self._create_jwt(
            session.user_id, session.fingerprint, self._resolve_user_role(profile.role)
        )
        session.refresh_token = self._generate_refresh_token()
        session.expires_at = self._get_session_expiration()
        session.status = SessionStatus.ACTIVE

        return await self.repository.update_session(session)

    async def refresh_token(self, request: TokenRefreshRequest) -> TokenRefreshResponse:
        session = await self.repository.get_session_by_refresh_token(request.refresh_token)
        self._validate_not_found(session, "Session", request.refresh_token)

        if session.status != SessionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Session is not active"
            )

        if session.expires_at < self._get_current_time():
            await self.repository.update_session_status(session.id, SessionStatus.EXPIRED)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

        refreshed = await self._refresh_session_tokens(session)
        self._log_operation("refresh_token", "Session", refreshed.id)
        return TokenRefreshResponse(
            access_token=refreshed.token,
            refresh_token=refreshed.refresh_token or "",
        )

    async def logout(self, session_id: UUID) -> bool:
        self._log_operation("logout", "Session", session_id)
        success = await self.repository.revoke_session(session_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        return success

    async def verify_token(self, token: str) -> UserSessionResponse:
        payload = self._decode_jwt(token)
        self._log_operation("verify_token", "User", payload.get("sub", token))

        session = await self.repository.fetch_user_session(token)
        self._validate_not_found(session, "Session", token)

        if session.status != SessionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Session is not active"
            )

        if session.expires_at < self._get_current_time():
            await self.repository.update_session_status(session.id, SessionStatus.EXPIRED)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

        return UserSessionResponse.model_validate(session)
