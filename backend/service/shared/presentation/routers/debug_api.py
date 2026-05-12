import json
import logging

from fastapi import APIRouter, Body, HTTPException

from service.composition import state as container
from service.infrastructure.messaging import stream_helpers

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/debug")


@router.get("/session/{token}")
async def get_session_by_token(token: str):
    """Debug endpoint: return session object stored for given session token (best-effort).

    NOTE: this is temporary and intended for local debugging only.
    """
    try:
        session_store = container.get_current_container().infra.redis_session_store
    except Exception as exc:
        logger.exception("Debug: RedisSessionStore not available: %s", exc)
        raise HTTPException(status_code=500, detail="Session store not available") from exc

    try:
        session = await session_store.get_session_by_token(token)
    except Exception as exc:
        logger.exception("Debug: error while reading session: %s", exc)
        raise HTTPException(status_code=500, detail="Error reading session") from exc

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/emit")
async def emit_stream_event(thread_id: str = Body(...), payload: dict = Body(...)):  # noqa: B008
    """Debug helper: emit a JSON payload into chat:{thread_id}:stream using the app's Redis client.

    This helps testing WS consumers using messages emitted from the same process.
    """
    try:
        redis_client = container.get_current_container().infra.redis_client
    except Exception as exc:
        logger.exception("Debug emit: Redis client not available: %s", exc)
        raise HTTPException(status_code=500, detail="Redis client not available") from exc
    try:
        await stream_helpers.xadd(
            redis_client,
            f"chat:{thread_id}:stream",
            {"data": json.dumps(payload)},
        )
    except Exception as exc:
        logger.exception("Debug emit: failed to xadd: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to emit event") from exc
    return {"status": "emitted"}
