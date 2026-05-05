from fastapi import APIRouter, WebSocket, status
import logging
import json
from service import container
from service.infrastructure.messaging import stream_helpers
from service.security import AuthValidator
from service.settings import config

logger = logging.getLogger(__name__)
router = APIRouter()

# Tunable limits for replay/claim behaviour to avoid overloading WS consumers
MAX_REPLAY = 200
MAX_CLAIM = 50
PEL_MIN_IDLE_MS = 60_000
from prometheus_client import Counter

# Metrics for jobs websocket
try:
    from prometheus_client import Gauge

    JOBS_REPLAY_SENT_TOTAL = Counter("jobs_replay_sent_total", "Number of replay entries sent to jobs websocket")
    JOBS_CLAIMED_SENT_TOTAL = Counter("jobs_claimed_sent_total", "Number of claimed entries successfully sent to jobs websocket")
    JOBS_CLAIMED_LEFT_UNACKED_TOTAL = Counter("jobs_claimed_left_unacked_total", "Number of claimed entries that couldn't be sent and left unacked (jobs)")
    JOBS_XACK_ERRORS_TOTAL = Counter("jobs_xack_errors_total", "Number of xack errors in jobs websocket")
    JOBS_XREAD_ERRORS_TOTAL = Counter("jobs_xread_errors_total", "Number of xread_group errors in jobs websocket")
    JOBS_CLAIMED_CURRENT = Gauge("jobs_claimed_current", "Number of currently claimed entries for jobs websocket")
except Exception:
    JOBS_REPLAY_SENT_TOTAL = JOBS_CLAIMED_SENT_TOTAL = JOBS_CLAIMED_LEFT_UNACKED_TOTAL = JOBS_XACK_ERRORS_TOTAL = JOBS_XREAD_ERRORS_TOTAL = JOBS_CLAIMED_CURRENT = None


@router.websocket("/api/jobs/v1/{job_id}/ws")
async def jobs_ws(websocket: WebSocket, job_id: str) -> None:
    """WebSocket endpoint for job/calendar streaming using Redis Streams.

    Uses stream key `job:{job_id}:stream` and mirrors BatchService behaviour for auth/session.
    """
    try:
        try:
            session_store = container.get_current_container().infra.redis_session_store
        except Exception:
            session_store = None
            logger.debug("jobs_ws: no session_store found in container")

        auth_validator = AuthValidator(config.auth)
        session = await auth_validator.authenticate_websocket(websocket, session_store)
        logger.debug("jobs_ws: session resolved=%s", session)
        if not session:
            logger.debug("jobs_ws: session invalid, closing")
            await websocket.accept()
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket.accept()
        logger.debug("jobs_ws: accepted websocket")

        try:
            redis_client = container.get_current_container().infra.redis_client
        except Exception:
            logger.debug("jobs_ws: redis client missing, closing")
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return

        logger.debug("jobs_ws: redis_client=%s", type(redis_client))

        stream_key = f"job:{job_id}:stream"
        group = f"job:{job_id}:group"
        consumer = websocket.headers.get("x-consumer-name") or f"ws:{id(websocket)}"
        logger.info("jobs_ws: consumer=%s connected for stream=%s", consumer, stream_key)

        last_id = websocket.query_params.get("last_id")

        try:
            logger.debug("jobs_ws: calling ensure_group for stream=%s group=%s", stream_key, group)
            await stream_helpers.ensure_group(redis_client, stream_key, group, mkstream=True)
            logger.debug("jobs_ws: ensure_group completed for stream=%s group=%s", stream_key, group)
        except Exception as e:
            logger.exception("jobs_ws: ensure_group failed: %s", e)
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return

        try:
            if last_id:
                # Bound replay to avoid overwhelming the websocket client
                replay_count = min(MAX_REPLAY, 100)
                entries = await stream_helpers.xrange(redis_client, stream_key, last_id, "+", count=replay_count)
                await process_replay_entries(websocket, entries)

            # Check pending entries and claim a bounded number to avoid overload
            pending = await stream_helpers.xpending(redis_client, stream_key, group)
            logger.debug("jobs_ws: pending returned=%s", pending)
            pending_count = pending.get("count", 0) if pending else 0
            if pending_count > 0:
                claim_limit = min(pending_count, MAX_CLAIM)
                try:
                    claimed = await stream_helpers.xauto_claim(
                        redis_client,
                        stream_key,
                        group,
                        consumer,
                        min_idle_ms=PEL_MIN_IDLE_MS,
                        count=claim_limit,
                    )
                except Exception:
                    logger.exception("jobs_ws: xauto_claim failed; continuing")
                    claimed = []
                logger.info("jobs_ws: claimed_count=%s for stream=%s group=%s", len(claimed), stream_key, group)
                # update claimed gauge and process claimed entries via helper for testability/metrics
                try:
                    if JOBS_CLAIMED_CURRENT is not None:
                        JOBS_CLAIMED_CURRENT.set(len(claimed))
                except Exception:
                    pass
                await process_jobs_claimed_entries(websocket, redis_client, stream_key, group, claimed)

            # start incoming loop to allow client to post messages (e.g., commands or inputs)
            async def _incoming_loop():
                try:
                    while True:
                        msg = await websocket.receive_json()
                        if not isinstance(msg, dict):
                            continue
                        # publish client message into job stream
                        payload = {"event": "client_message", "id": msg.get("id"), "payload": msg}
                        try:
                            try:
                                await stream_helpers.xadd(redis_client, stream_key, {"data": json.dumps(payload)})
                                try:
                                    await websocket.send_json({"type": "client_message_ack", "id": msg.get("id")})
                                except Exception:
                                    logger.debug("jobs_ws: failed to send ack for client message", exc_info=True)
                            except Exception:
                                logger.debug("jobs_ws: failed to xadd client message", exc_info=True)
                        except Exception:
                            logger.debug("jobs_ws: failed to xadd client message", exc_info=True)
                except Exception:
                    logger.debug("jobs_ws: incoming loop ended", exc_info=True)

            import asyncio as _asyncio

            incoming_task = _asyncio.create_task(_incoming_loop())

            # simple backoff for redis/read errors
            _backoff = 0.2
            _max_backoff = 5.0

            while True:
                # non-blocking check for incoming client messages (helps tests and reduces race)
                try:
                    try:
                        msg = await _asyncio.wait_for(websocket.receive_json(), timeout=0.01)
                    except _asyncio.TimeoutError:
                        msg = None
                    if msg and isinstance(msg, dict):
                        payload = {"event": "client_message", "id": msg.get("id"), "payload": msg}
                        try:
                            try:
                                await stream_helpers.xadd(redis_client, stream_key, {"data": json.dumps(payload)})
                                try:
                                    await websocket.send_json({"type": "client_message_ack", "id": msg.get("id")})
                                except Exception:
                                    logger.debug("jobs_ws: failed to send ack for client message", exc_info=True)
                            except Exception:
                                logger.debug("jobs_ws: failed to xadd client message from main loop", exc_info=True)
                        except Exception:
                            logger.debug("jobs_ws: failed to xadd client message from main loop", exc_info=True)
                except Exception:
                    # swallow errors from non-blocking receive here
                    pass

                logger.debug("jobs_ws: calling xread_group group=%s consumer=%s streams=%s", group, consumer, {stream_key: ">"})
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
                    try:
                        if JOBS_XREAD_ERRORS_TOTAL:
                            JOBS_XREAD_ERRORS_TOTAL.inc()
                    except Exception:
                        pass
                    logger.exception("jobs_ws: xread_group failed, backing off %s seconds", _backoff)
                    await asyncio.sleep(min(_backoff, _max_backoff))
                    _backoff = min(_backoff * 2, _max_backoff)
                    continue

                logger.debug("jobs_ws: xread_group returned %s", res)
                if not res:
                    try:
                        await websocket.send_json({"type": "heartbeat"})
                    except Exception:
                        raise
                    continue

                for sname, messages in res:
                    for entry_id, fields in messages:
                        logger.debug("jobs_ws: received entry id=%s fields=%s", entry_id, fields)
                        payload = _parse_payload(fields)
                        await websocket.send_json({"id": entry_id, "data": payload})
                        await stream_helpers.xack(redis_client, stream_key, group, entry_id)

        except Exception as exc:
            logger.exception("Error in jobs websocket stream: %s", exc)
            try:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            except Exception:
                logger.debug("Failed to close websocket after error", exc_info=True)
        finally:
            try:
                incoming_task.cancel()
            except Exception:
                pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


def _parse_payload(fields: dict) -> dict:
    try:
        data = fields.get("data") if isinstance(fields, dict) else fields
    except Exception:
        data = fields
    try:
        import json

        return json.loads(data) if isinstance(data, str) else data
    except Exception:
        return data


async def process_replay_entries(websocket, entries: list):
    """Send XRANGE replay entries to websocket and update replay metric for jobs_ws."""
    for entry_id, fields in entries:
        payload = _parse_payload(fields)
        try:
            await websocket.send_json({"id": entry_id, "data": payload})
            try:
                if JOBS_REPLAY_SENT_TOTAL:
                    JOBS_REPLAY_SENT_TOTAL.inc()
            except Exception:
                pass
        except Exception:
            logger.debug("jobs_ws: failed to send replay entry %s", entry_id, exc_info=True)

async def process_jobs_claimed_entries(websocket, redis_client, stream_key: str, group: str, claimed: list):
    """Process a list of claimed entries for jobs_ws: send then ack on success.

    Extracted for tests and metrics.
    """
    for entry_id, fields in claimed:
        payload = _parse_payload(fields)
        try:
            await websocket.send_json({"id": entry_id, "data": payload})
            try:
                if JOBS_CLAIMED_SENT_TOTAL:
                    JOBS_CLAIMED_SENT_TOTAL.inc()
            except Exception:
                pass
        except Exception:
            try:
                if JOBS_CLAIMED_LEFT_UNACKED_TOTAL:
                    JOBS_CLAIMED_LEFT_UNACKED_TOTAL.inc()
            except Exception:
                pass
            logger.debug("jobs_ws: failed to send claimed entry %s; leaving unacked", entry_id, exc_info=True)
            continue

        try:
            await stream_helpers.xack(redis_client, stream_key, group, entry_id)
        except Exception:
            try:
                if JOBS_XACK_ERRORS_TOTAL:
                    JOBS_XACK_ERRORS_TOTAL.inc()
            except Exception:
                pass
            logger.debug("jobs_ws: xack failed for %s; continuing", entry_id, exc_info=True)
