import logging

from fastapi import WebSocket, status

from service.security import AuthValidator

logger = logging.getLogger(__name__)


class ChatWsAuthService:
    def __init__(self, validator: AuthValidator, session_store) -> None:
        self._validator = validator
        self._session_store = session_store

    async def authenticate(self, websocket: WebSocket) -> dict | None:
        try:
            session = await self._validator.authenticate_websocket(websocket, self._session_store)
            if not session:
                await websocket.accept()
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return None
            await websocket.accept()
            return session
        except Exception as exc:
            logger.exception("Authentication failed: %s", exc)
            try:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            except Exception:
                pass
            return None
