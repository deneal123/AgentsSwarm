from fastapi import APIRouter, HTTPException
from service import container
import logging
from fastapi import Body
from service.infrastructure.messaging import stream_helpers
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/debug")


@router.get("/session/{token}")
async def get_session_by_token(token: str):
    """Debug endpoint: return session object stored for given session token (best-effort).

    NOTE: this is temporary and intended for local debugging only.
    """
    try:
        session_store = container.get_current_container().infra.redis_session_store
    except Exception as e:
        logger.exception("Debug: RedisSessionStore not available: %s", e)
        raise HTTPException(status_code=500, detail="Session store not available")

    try:
        session = await session_store.get_session_by_token(token)
    except Exception as e:
        logger.exception("Debug: error while reading session: %s", e)
        raise HTTPException(status_code=500, detail="Error reading session")

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/emit")
async def emit_stream_event(thread_id: str = Body(...), payload: dict = Body(...)):
    """Debug helper: emit a JSON payload into chat:{thread_id}:stream using the app's Redis client.

    This helps testing WS consumers using messages emitted from the same process.
    """
    try:
        redis_client = container.get_current_container().infra.redis_client
    except Exception as e:
        logger.exception("Debug emit: Redis client not available: %s", e)
        raise HTTPException(status_code=500, detail="Redis client not available")
    try:
        await stream_helpers.xadd(redis_client, f"chat:{thread_id}:stream", {"data": json.dumps(payload)})
    except Exception as e:
        logger.exception("Debug emit: failed to xadd: %s", e)
        raise HTTPException(status_code=500, detail="Failed to emit event")
    return {"status": "emitted"}
