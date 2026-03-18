"""WebSocket authentication helpers for FastAPI routers."""

from fastapi import HTTPException, status, WebSocket

from service.presentation.dependencies.auth import get_current_user
from service.models.enums import UserType


def _extract_token(websocket: WebSocket) -> str | None:
    """Get auth token from cookies or ?token query parameter."""
    cookies = websocket.cookies or {}
    token = cookies.get("auth_token")
    if token:
        return token
    return websocket.query_params.get("token")


async def authenticate_websocket(
    websocket: WebSocket,
    resource_id: str,
    resource_type: str,
) -> dict[str, str] | None:
    """Validate JWT for WebSocket connection and return auth context."""
    token = _extract_token(websocket)

    if not token:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication required",
        )
        return None

    try:
        profile = get_current_user(auth_token=token)
    except HTTPException as exc:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=str(exc.detail))
        return None

    return {
        "user_id": profile.user_id,
        "user_type": profile.type.value if isinstance(profile.type, UserType) else str(profile.type),
        "auth_type": profile.type.name if isinstance(profile.type, UserType) else "unknown",
    }
