import asyncio
import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, WebSocket, status
from prometheus_client import Counter, Gauge

from service.composition.state import get_optional_redis_client, get_optional_redis_session_store
from service.infrastructure.messaging import stream_helpers
from service.settings import config
from service.shared.security.auth_validation import AuthValidator

logger = logging.getLogger(__name__)
router = APIRouter()

_MAX_REPLAY = config.chat_ws.settings.max_replay
_MAX_CLAIM = config.chat_ws.settings.max_claim
_PEL_MIN_IDLE_MS = config.chat_ws.settings.pel_min_idle_ms

try:
    JOBS_REPLAY_SENT_TOTAL = Counter("jobs_replay_sent_total", "Replay entries sent to jobs WS")
    JOBS_CLAIMED_SENT_TOTAL = Counter("jobs_claimed_sent_total", "Claimed entries sent to jobs WS")
    JOBS_CLAIMED_LEFT_UNACKED_TOTAL = Counter(
        "jobs_claimed_left_unacked_total",
        "Claimed entries left unacked in jobs WS",
    )
    JOBS_XACK_ERRORS_TOTAL = Counter("jobs_xack_errors_total", "xack errors in jobs WS")
    JOBS_XREAD_ERRORS_TOTAL = Counter("jobs_xread_errors_total", "xread_group errors in jobs WS")
    JOBS_CLAIMED_CURRENT = Gauge("jobs_claimed_current", "Currently claimed entries in jobs WS")
except Exception:
    JOBS_REPLAY_SENT_TOTAL = JOBS_CLAIMED_SENT_TOTAL = JOBS_CLAIMED_LEFT_UNACKED_TOTAL = None
    JOBS_XACK_ERRORS_TOTAL = JOBS_XREAD_ERRORS_TOTAL = JOBS_CLAIMED_CURRENT = None


def _parse_payload(fields: dict) -> dict[str, Any]:
    data = fields.get("data") if isinstance(fields, dict) else fields
    try:
        parsed = json.loads(data) if isinstance(data, str) else data
    except Exception:
        parsed = data
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def _inc(metric) -> None:
    if metric is not None:
        try:
            metric.inc()
        except Exception:
            pass


async def process_replay_entries(websocket: WebSocket, entries: list) -> None:
    for entry_id, fields in entries:
        payload = _parse_payload(fields)
        try:
            await websocket.send_json({"id": entry_id, "data": payload})
            _inc(JOBS_REPLAY_SENT_TOTAL)
        except Exception:
            logger.debug("jobs_ws: failed to send replay entry %s", entry_id, exc_info=True)


async def process_jobs_claimed_entries(
    websocket: WebSocket,
    redis_client,
    stream_key: str,
    group: str,
    claimed: list,
) -> None:
    for entry_id, fields in claimed:
        payload = _parse_payload(fields)
        try:
            await websocket.send_json({"id": entry_id, "data": payload})
            _inc(JOBS_CLAIMED_SENT_TOTAL)
        except Exception:
            _inc(JOBS_CLAIMED_LEFT_UNACKED_TOTAL)
            logger.debug(
                "jobs_ws: failed to send claimed entry %s; leaving unacked",
                entry_id,
                exc_info=True,
            )
            continue
        try:
            await stream_helpers.xack(redis_client, stream_key, group, entry_id)
        except Exception:
            _inc(JOBS_XACK_ERRORS_TOTAL)
            logger.debug("jobs_ws: xack failed for %s; continuing", entry_id, exc_info=True)


@router.websocket("/api/jobs/v1/{job_id}/ws")
async def jobs_ws(
    websocket: WebSocket,
    job_id: str,
    session_store: Annotated[Any, Depends(get_optional_redis_session_store)],
    redis_client: Annotated[Any, Depends(get_optional_redis_client)],
) -> None:
    """WebSocket endpoint for job/calendar streaming using Redis Streams."""
    try:
        auth_validator = AuthValidator(config.auth)
        session = await auth_validator.authenticate_websocket(websocket, session_store)
        if not session:
            await websocket.accept()
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket.accept()

        if redis_client is None:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return

        stream_key = f"job:{job_id}:stream"
        group = f"job:{job_id}:group"
        consumer = websocket.headers.get("x-consumer-name") or f"ws:{id(websocket)}"
        last_id = websocket.query_params.get("last_id")

        logger.info("jobs_ws: consumer=%s connected for stream=%s", consumer, stream_key)

        try:
            await stream_helpers.ensure_group(redis_client, stream_key, group, mkstream=True)
        except Exception as exc:
            logger.exception("jobs_ws: ensure_group failed: %s", exc)
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return

        if last_id:
            entries = await stream_helpers.xrange(
                redis_client, stream_key, last_id, "+", count=min(_MAX_REPLAY, 100)
            )
            await process_replay_entries(websocket, entries)

        pending = await stream_helpers.xpending(redis_client, stream_key, group)
        pending_count = pending.get("count", 0) if pending else 0
        if pending_count > 0:
            try:
                claimed = await stream_helpers.xauto_claim(
                    redis_client,
                    stream_key,
                    group,
                    consumer,
                    min_idle_ms=_PEL_MIN_IDLE_MS,
                    count=min(pending_count, _MAX_CLAIM),
                )
            except Exception:
                logger.exception("jobs_ws: xauto_claim failed; continuing")
                claimed = []

            if JOBS_CLAIMED_CURRENT is not None:
                try:
                    JOBS_CLAIMED_CURRENT.set(len(claimed))
                except Exception:
                    pass

            await process_jobs_claimed_entries(websocket, redis_client, stream_key, group, claimed)

        async def _publish_client_message(msg: dict) -> None:
            payload = {"event": "client_message", "id": msg.get("id"), "payload": msg}
            try:
                await stream_helpers.xadd(redis_client, stream_key, {"data": json.dumps(payload)})
                await websocket.send_json({"type": "client_message_ack", "id": msg.get("id")})
            except Exception:
                logger.debug("jobs_ws: failed to publish client message", exc_info=True)

        async def _incoming_loop() -> None:
            try:
                while True:
                    msg = await websocket.receive_json()
                    if isinstance(msg, dict):
                        await _publish_client_message(msg)
            except Exception:
                logger.debug("jobs_ws: incoming loop ended", exc_info=True)

        incoming_task = asyncio.create_task(_incoming_loop())
        _backoff = 0.2
        _max_backoff = 5.0

        try:
            while True:
                try:
                    res = await stream_helpers.xread_group(
                        redis_client,
                        group,
                        consumer,
                        streams={stream_key: ">"},
                        count=10,
                        block=5000,
                    )
                    _backoff = 0.2
                except Exception:
                    _inc(JOBS_XREAD_ERRORS_TOTAL)
                    logger.exception("jobs_ws: xread_group failed, backing off %.1fs", _backoff)
                    await asyncio.sleep(min(_backoff, _max_backoff))
                    _backoff = min(_backoff * 2, _max_backoff)
                    continue

                if not res:
                    try:
                        await websocket.send_json({"type": "heartbeat"})
                    except Exception:
                        raise
                    continue

                for _sname, messages in res:
                    for entry_id, fields in messages:
                        payload = _parse_payload(fields)
                        await websocket.send_json({"id": entry_id, "data": payload})
                        await stream_helpers.xack(redis_client, stream_key, group, entry_id)
        except Exception as exc:
            logger.exception("jobs_ws: stream error: %s", exc)
            try:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            except Exception:
                pass
        finally:
            incoming_task.cancel()

    finally:
        try:
            await websocket.close()
        except Exception:
            pass
