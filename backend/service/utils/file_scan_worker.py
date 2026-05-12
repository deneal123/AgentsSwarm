import asyncio
import json
import logging
from typing import Any

from service.composition import state as container

logger = logging.getLogger(__name__)

SCAN_QUEUE_KEY = "file:scan:queue"


async def process_scan_once(redis_client: Any, scanner: Any) -> int:
    """Process one file from the scan queue (LPOP). Returns 1 if processed, 0 if nothing to do."""
    try:
        # Check if redis client has list pop methods (both sync and async)
        lpop = getattr(redis_client, "lpop", None)
        if not callable(lpop):
            # No list pop available
            logger.debug("Redis client has no lpop method; cannot process scan queue")
            return 0

        item = await lpop(SCAN_QUEUE_KEY)

        if not item:
            # nothing to do
            return 0

        # if bytes, decode
        if isinstance(item, bytes):
            try:
                item = item.decode("utf-8")
            except Exception:
                pass

        file_key = item
        logger.info("Processing file scan for %s", file_key)

        result = await scanner.scan(file_key)

        # Publish result to Redis Stream for consumers
        payload_json = json.dumps({"event": "scanned", "file_key": file_key, "result": result})
        # Prefer using our stream helper when available; fall back to direct client xadd as last resort.
        try:
            try:
                from service.infrastructure.messaging import stream_helpers as _sh
            except Exception:
                _sh = None

            published = False
            if _sh is not None:
                try:
                    await _sh.xadd(redis_client, f"file:{file_key}:stream", {"data": payload_json})
                    published = True
                except Exception:
                    logger.debug("stream_helpers.xadd failed, falling back to direct xadd", exc_info=True)

            # best-effort: try direct xadd if available (some clients are sync) only if we didn't publish
            if not published:
                try:
                    client_stream_add = getattr(redis_client, "xadd", None)
                    if callable(client_stream_add):
                        res = client_stream_add(f"file:{file_key}:stream", {"data": payload_json})
                        import inspect
                        if inspect.isawaitable(res):
                            await res
                except Exception:
                    logger.debug("Failed to publish scan result to Redis stream", exc_info=True)
        except Exception:
            # outer safety - ensure any unexpected error doesn't break processing
            logger.debug("Unexpected error while publishing scan result", exc_info=True)

        logger.info("File scan completed for %s: %s", file_key, result)
        return 1

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception("Error processing file scan: %s", e)
        return 0


async def scan_loop():
    """Main loop to run as a background task, popping items and scanning them."""
    try:
        redis_client = None
        try:
            redis_client = container.get_current_container().infra.redis_client
        except Exception:
            redis_client = None

        scanner = None
        try:
            scanner = container.get_current_container().infra.file_scanner
        except Exception:
            logger.warning("FileScanner not registered; exiting scan loop")
            return

        while True:
            processed = await process_scan_once(redis_client, scanner)
            if processed == 0:
                await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("File scan loop cancelled")
        raise
    except Exception as e:
        logger.exception("File scan loop failed: %s", e)
        # bubble up to background manager which will restart the task
        raise
