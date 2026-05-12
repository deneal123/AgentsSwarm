from dataclasses import dataclass

import jwt
from fastapi import HTTPException, status
from fastapi.websockets import WebSocket

from service.models.auth_models import AuthProfile
from service.settings import AuthConfig


class AuthTelemetry:
    def __init__(self) -> None:
        self._counter = None
        try:
            from prometheus_client import Counter

            self._counter = Counter(
                "auth_validation_failures_total",
                "Authentication validation failures",
                ["surface", "reason", "channel"],
            )
        except Exception:
            self._counter = None

    def record_failure(self, *, surface: str, reason: str, channel: str = "none") -> None:
        if self._counter is None:
            return
        try:
            self._counter.labels(surface=surface, reason=reason, channel=channel).inc()
        except Exception:
            return


@dataclass(slots=True)
class WsTokenCandidate:
    channel: str
    token: str


class AuthValidator:
    def __init__(self, auth_config: AuthConfig, telemetry: AuthTelemetry | None = None) -> None:
        self._auth_config = auth_config
        self._telemetry = telemetry or AuthTelemetry()

    def validate_http_jwt(self, auth_token: str | None) -> AuthProfile:
        if not auth_token:
            self._telemetry.record_failure(surface="http", reason="missing_token")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")

        try:
            payload: dict = jwt.decode(
                auth_token,
                self._auth_config.secret,
                algorithms=[self._auth_config.algorithm],
            )
            return AuthProfile(
                user_id=payload["sub"],
                fingerprint=payload.get("fingerprint"),
                type=payload["type"],
            )
        except jwt.ExpiredSignatureError as exc:
            self._telemetry.record_failure(
                surface="http",
                reason="jwt_expired",
                channel="jwt_cookie",
            )
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token expired") from exc
        except jwt.InvalidTokenError as exc:
            self._telemetry.record_failure(
                surface="http",
                reason="jwt_invalid",
                channel="jwt_cookie",
            )
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    async def authenticate_websocket(self, websocket: WebSocket, session_store) -> dict | None:
        jwt_cookie = websocket.cookies.get("auth_token")
        if jwt_cookie:
            if not self._is_channel_allowed("jwt_cookie"):
                self._telemetry.record_failure(
                    surface="ws", reason="channel_blocked", channel="jwt_cookie"
                )
                return None
            try:
                payload: dict = jwt.decode(
                    jwt_cookie,
                    self._auth_config.secret,
                    algorithms=[self._auth_config.algorithm],
                )
                return {
                    "id": f"auth:{payload.get('sub')}",
                    "user_id": payload.get("sub"),
                    "type": payload.get("type", "auth"),
                }
            except jwt.PyJWTError:
                self._telemetry.record_failure(
                    surface="ws",
                    reason="jwt_invalid",
                    channel="jwt_cookie",
                )
                return None

        token_candidate = self._get_ws_token_candidate(websocket)
        if token_candidate is None:
            self._telemetry.record_failure(surface="ws", reason="missing_token")
            return None

        if not self._is_channel_allowed(token_candidate.channel):
            self._telemetry.record_failure(
                surface="ws",
                reason="channel_blocked",
                channel=token_candidate.channel,
            )
            return None

        token = token_candidate.token
        if token == "anon-token":
            if not self._is_channel_allowed("anon_token"):
                self._telemetry.record_failure(
                    surface="ws",
                    reason="channel_blocked",
                    channel="anon_token",
                )
                return None
            return {"id": "anon-session", "user_id": "00000000-0000-0000-0000-000000000000"}

        if token == "test-token":
            if (
                self._auth_config.auth_mode == "prod"
                and self._auth_config.enforce_prod_runtime_auth_guard
            ):
                self._telemetry.record_failure(
                    surface="ws",
                    reason="dev_token_forbidden_prod",
                    channel=token_candidate.channel,
                )
                return None
            if not self._auth_config.enable_dev_test_token:
                self._telemetry.record_failure(
                    surface="ws",
                    reason="dev_token_feature_disabled",
                    channel=token_candidate.channel,
                )
                return None
            return {"id": "test-session", "user_id": "e53439c1-cec2-45ab-8854-9e13efda26e3"}

        if not self._auth_config.enable_legacy_ws_token_auth:
            self._telemetry.record_failure(
                surface="ws", reason="legacy_disabled", channel=token_candidate.channel
            )
            return None

        if session_store is None:
            self._telemetry.record_failure(surface="ws", reason="session_store_missing")
            return None

        session = await session_store.get_session_by_token(token)
        if not session:
            self._telemetry.record_failure(
                surface="ws", reason="session_not_found", channel=token_candidate.channel
            )
            return None
        return session

    def _get_ws_token_candidate(self, websocket: WebSocket) -> WsTokenCandidate | None:
        query_token = websocket.query_params.get("token")
        if query_token:
            return WsTokenCandidate(channel="query_token", token=query_token)

        header = websocket.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            return WsTokenCandidate(
                channel="authorization_bearer",
                token=header.split(" ", 1)[1].strip(),
            )

        cookie_session_token = websocket.cookies.get("session_token")
        if cookie_session_token:
            return WsTokenCandidate(channel="session_cookie", token=cookie_session_token)

        cookie_session = websocket.cookies.get("session")
        if cookie_session:
            return WsTokenCandidate(channel="session_cookie", token=cookie_session)

        return None

    def _is_channel_allowed(self, channel: str) -> bool:
        allowed = (
            self._auth_config.ws_auth_allowlist_prod
            if self._auth_config.auth_mode == "prod"
            else self._auth_config.ws_auth_allowlist_dev
        )
        return channel in allowed
