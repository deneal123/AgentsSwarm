"""Helpers for working with Redis Streams in an aioredis-like client.

Provides thin wrappers used by the WebSocket consumer and workers. These are
kept small to make unit-testing (with fakes) straightforward.
"""

import asyncio
import inspect
import logging
from typing import Any

from prometheus_client import Counter, Gauge

logger = logging.getLogger(__name__)

# Redis Streams metrics
REDIS_STREAM_LENGTH = Gauge("redis_stream_length", "Redis Stream length", ["stream_key"])

REDIS_CONSUMER_LAG = Gauge(
    "redis_consumer_lag",
    "Redis Consumer lag (pending messages)",
    ["stream_key", "group", "consumer"],
)


async def ensure_group(redis_client, stream: str, group: str, mkstream: bool = False):
    """Ensure consumer group exists. Ignores if already exists."""
    try:
        fn = getattr(redis_client, "xgroup_create", None)
        if not fn:
            logger.warning("ensure_group: xgroup_create method not found on redis_client")
            return
        try:
            res = fn(stream, group, id="0", mkstream=mkstream)
        except TypeError:
            try:
                res = fn(stream, group, "0", mkstream=mkstream)
            except TypeError:
                res = fn(stream, group, "0")
        if inspect.isawaitable(res):
            await res
        else:
            await asyncio.to_thread(lambda: fn(stream, group, "0", mkstream=mkstream))
    except Exception as e:
        logger.debug(f"ensure_group: exception (likely group exists): {e}")
        return


async def xrange(
    redis_client,
    stream: str,
    start: str,
    end: str,
    count: int = 100,
) -> list[tuple[str, dict[str, Any]]]:
    """Return entries in range [start, end].

    Expected return: List[(id, {field: value})]
    """
    fn = getattr(redis_client, "xrange", None)
    if fn is None:
        return []
    try:
        res = fn(stream, start, end, count=count)
    except TypeError:
        # Fallback to thread call if signature mismatches
        return await asyncio.to_thread(fn, stream, start, end, count)
    if inspect.isawaitable(res):
        res = await res
    else:
        # For sync clients, execute in thread to avoid blocking
        res = await asyncio.to_thread(fn, stream, start, end, count)
    return res or []


async def xread(
    redis_client,
    streams: dict[str, str],
    count: int = 10,
    block: int = 0,
):
    """Read messages from Redis streams.

    Returns the raw aioredis result: list of (stream, [(id, fields), ...])
    """
    # aioredis: xread(streams=..., count=..., timeout=...)
    fn = getattr(redis_client, "xread", None)
    if not fn:
        return []

    # check the class method for coroutineness
    try:
        res = fn(streams=streams, count=count, timeout=block)
    except TypeError:
        try:
            # some sync clients use different arg order
            res = fn(streams, count, block)
        except Exception:
            return []
    if inspect.isawaitable(res):
        res = await res
    else:
        res = await asyncio.to_thread(fn, streams, count, block)
    return res or []


async def xread_group(
    redis_client,
    group: str,
    consumer: str,
    streams: dict[str, str],
    count: int = 10,
    block: int = 0,
):
    """Read new messages via consumer group.

    Returns the raw aioredis result: list of (stream, [(id, fields), ...])
    """
    # aioredis: xread_group(groupname, consumername, streams=..., count=..., timeout=...)
    fn = (
        getattr(redis_client, "xread_group", None)
        or getattr(redis_client, "xreadgroup", None)
        or getattr(redis_client, "xread_group", None)
    )
    if not fn:
        return []
    # check the class method for coroutineness
    try:
        res = fn(group, consumer, streams=streams, count=count, timeout=block)
    except TypeError:
        try:
            # some sync clients use different arg order
            res = fn(group, consumer, streams, count, block)
        except Exception:
            return []
    if inspect.isawaitable(res):
        res = await res
    else:
        res = await asyncio.to_thread(fn, group, consumer, streams, count, block)
    return res or []


async def xack(redis_client, stream: str, group: str, message_id: str):
    fn = getattr(redis_client, "xack", None)
    if not fn:
        return
    try:
        res = fn(stream, group, message_id)
    except TypeError:
        return await asyncio.to_thread(fn, stream, group, message_id)
    if inspect.isawaitable(res):
        await res
    else:
        await asyncio.to_thread(fn, stream, group, message_id)


async def xpending(redis_client, stream: str, group: str) -> dict[str, Any]:
    """Return summary of pending messages for the group.

    We return at least {'count': int}. Implementations may return more.
    """
    try:
        fn = getattr(redis_client, "xpending", None)
        if not fn:
            return {"count": 0}
        try:
            res = fn(stream, group)
        except TypeError:
            return await asyncio.to_thread(fn, stream, group)
        if inspect.isawaitable(res):
            info = await res
        else:
            info = await asyncio.to_thread(fn, stream, group)
        return info or {"count": 0}
    except Exception:
        return {"count": 0}


async def xauto_claim(
    redis_client,
    stream: str,
    group: str,
    consumer: str,
    min_idle_ms: int = 60_000,
    start_id: str = "0-0",
    count: int = 100,
):
    """Claim idle messages and return entries list [(id, fields), ...]."""
    try:
        # aioredis may expose xautoclaim or xauto_claim
        if hasattr(redis_client, "xautoclaim") or hasattr(redis_client, "xauto_claim"):
            # prefer async method if present
            fn = getattr(redis_client, "xautoclaim", None) or getattr(
                redis_client, "xauto_claim", None
            )
            if not fn:
                return []
            try:
                res = fn(stream, group, consumer, min_idle_ms, start_id, count)
            except TypeError:
                # try alternate signature
                try:
                    res = fn(stream, group, consumer, min_idle_ms, start_id, count=count)
                except Exception:
                    return []
            if inspect.isawaitable(res):
                res = await res
            else:
                res = await asyncio.to_thread(
                    fn, stream, group, consumer, min_idle_ms, start_id, count
                )
            # xautoclaim returns (next_start, entries)
            if isinstance(res, tuple) and len(res) == 2:
                return res[1] or []
            return res or []
        else:
            # Fallback: try xclaim after xpending listing (not implemented here)
            return []

    except Exception:
        # metric: xauto_claim failure
        try:
            XAUTOCLAIM_FAILED.inc()
        except Exception:
            pass
        return []


async def xadd(redis_client, stream: str, mapping: dict[str, Any]):
    """Unified async xadd wrapper.

    Supports both async and sync redis clients. If the client's xadd returns an
    awaitable, it will be awaited; otherwise the result is returned directly.
    """
    xadd_fn = getattr(redis_client, "xadd", None)
    if not callable(xadd_fn):
        raise AttributeError("redis client has no xadd method")
    try:
        if inspect.iscoroutinefunction(xadd_fn):
            return await xadd_fn(stream, mapping)
        # run sync xadd in thread to avoid blocking
        return await asyncio.to_thread(xadd_fn, stream, mapping)
    except Exception:
        try:
            XADD_ERRORS.inc()
        except Exception:
            pass
        raise


def xadd_sync(redis_client, stream: str, mapping: dict[str, Any]):
    """Synchronous helper for xadd usable in non-async contexts (e.g. Celery tasks).

    If the client's xadd returns an awaitable, it will be executed inside a
    fresh event loop using asyncio.run.
    """
    xadd_fn = getattr(redis_client, "xadd", None)
    if not callable(xadd_fn):
        raise AttributeError("redis client has no xadd method")
    try:
        if inspect.iscoroutinefunction(xadd_fn):
            return asyncio.run(xadd_fn(stream, mapping))
        return xadd_fn(stream, mapping)
    except Exception:
        try:
            XADD_ERRORS.inc()
        except Exception:
            pass
        raise


async def worker_consume_loop(
    redis_client,
    stream: str,
    group: str,
    consumer: str,
    process_func,
    *,
    count: int = 10,
    block: int = 5000,
):
    """Simple worker loop that reads from a consumer group, calls process_func on each message
    and XACKs after successful processing.

    process_func should be an async callable taking (message_id, fields) and may raise on failure.
    This helper is intentionally small so unit-tests can patch `redis_client` with a fake and
    assert expected calls (xread_group/xack).
    """
    while True:
        res = await xread_group(
            redis_client,
            group,
            consumer,
            streams={stream: ">"},
            count=count,
            block=block,
        )
        if not res:
            # nothing to do, continue
            continue
        for _sname, messages in res:
            for message_id, fields in messages:
                try:
                    await process_func(message_id, fields)
                    await xack(redis_client, stream, group, message_id)
                except Exception:
                    # leave in PEL for retries / claim by others
                    continue


async def worker_consume_once(
    redis_client,
    stream: str,
    group: str,
    consumer: str,
    process_func,
    *,
    count: int = 10,
    block: int = 0,
):
    """Perform a single read/process/ack iteration and return number processed."""
    res = await xread_group(
        redis_client,
        group,
        consumer,
        streams={stream: ">"},
        count=count,
        block=block,
    )
    if not res:
        return 0
    processed = 0
    for _sname, messages in res:
        for message_id, fields in messages:
            try:
                await process_func(message_id, fields)
                await xack(redis_client, stream, group, message_id)
                processed += 1
            except Exception:
                continue
    return processed


async def reclaim_and_process(
    redis_client,
    stream: str,
    group: str,
    consumer: str,
    process_func,
    *,
    min_idle_ms: int = 60_000,
    start_id: str = "0-0",
    count: int = 100,
):
    """Claim idle messages (XAUTOCLAIM) and process them.

    Returns number of processed messages. This is intentionally synchronous in
    behaviour (single-shot) so it's easy to test.
    """
    processed = 0
    entries = await xauto_claim(
        redis_client,
        stream,
        group,
        consumer,
        min_idle_ms=min_idle_ms,
        start_id=start_id,
        count=count,
    )
    for entry_id, fields in entries:
        try:
            await process_func(entry_id, fields)
            await xack(redis_client, stream, group, entry_id)
            processed += 1
            try:
                RECLAIMED_PROCESSED.inc()
            except Exception:
                pass
        except Exception:
            # leave unacked for later retry/claim
            continue
    return processed


# Prometheus metrics
try:
    # follow Prometheus naming convention with _total suffix for counters
    XADD_ERRORS = Counter("stream_xadd_errors_total", "Number of errors while performing XADD")
    XAUTOCLAIM_FAILED = Counter(
        "stream_xautoclaim_failed_total", "Number of failures calling XAUTOCLAIM/XAUTCLAIM"
    )
    RECLAIMED_PROCESSED = Counter(
        "stream_reclaimed_processed_total", "Number of entries processed after reclaim"
    )
except Exception:
    # If prometheus is not available in import-time, fall back silently.
    XADD_ERRORS = XAUTOCLAIM_FAILED = RECLAIMED_PROCESSED = None


async def get_stream_info(redis_client, stream: str) -> dict[str, Any]:
    """Get stream information (length, groups, consumers)."""
    try:
        # Support both async and sync clients
        fn = getattr(redis_client, "xinfo_stream", None)
        if not fn:
            logger.warning("get_stream_info: xinfo_stream method not found on redis_client")
            return {}

        method = getattr(type(redis_client), "xinfo_stream", None)
        if inspect.iscoroutinefunction(method):
            info = await fn(stream)
        else:
            info = await asyncio.to_thread(lambda: fn(stream))

        groups = []
        try:
            groups_fn = getattr(redis_client, "xinfo_groups", None)
            if groups_fn:
                groups_method = getattr(type(redis_client), "xinfo_groups", None)
                if inspect.iscoroutinefunction(groups_method):
                    groups = await groups_fn(stream)
                else:
                    groups = await asyncio.to_thread(lambda: groups_fn(stream))
        except Exception:
            # Groups may not exist
            pass

        stream_length = info.get("length", 0)
        REDIS_STREAM_LENGTH.labels(stream_key=stream).set(stream_length)

        return {
            "length": stream_length,
            "groups": len(groups) if groups else 0,
            "first_entry": info.get("first-entry"),
            "last_entry": info.get("last-entry"),
            "groups_info": groups,
        }
    except Exception as e:
        logger.warning(f"Failed to get stream info for {stream}: {e}")
        return {}


async def get_consumer_lag(redis_client, stream: str, group: str, consumer: str) -> int | None:
    """Get consumer lag (number of pending messages for consumer)."""
    try:
        # Support both async and sync clients
        fn = getattr(redis_client, "xpending", None)
        if not fn:
            logger.warning("get_consumer_lag: xpending method not found on redis_client")
            return None

        method = getattr(type(redis_client), "xpending", None)
        if inspect.iscoroutinefunction(method):
            pending_info = await fn(stream, group)
        else:
            pending_info = await asyncio.to_thread(lambda: fn(stream, group))

        if isinstance(pending_info, dict):
            lag = pending_info.get("count", 0)
        else:
            # Legacy format or different client
            lag = len(pending_info) if pending_info else 0

        REDIS_CONSUMER_LAG.labels(stream_key=stream, group=group, consumer=consumer).set(lag)

        return lag
    except Exception as e:
        logger.warning(f"Failed to get consumer lag for {stream}/{group}/{consumer}: {e}")
        return None


async def trim_stream(redis_client, stream: str, maxlen: int = 1000):
    """Trim stream to maxlen entries (keep recent)."""
    try:
        # Support both async and sync clients
        fn = getattr(redis_client, "xtrim", None)
        if not fn:
            logger.warning("trim_stream: xtrim method not found on redis_client")
            return

        method = getattr(type(redis_client), "xtrim", None)
        if inspect.iscoroutinefunction(method):
            await fn(stream, maxlen=maxlen, approximate=True)
        else:
            await asyncio.to_thread(lambda: fn(stream, maxlen=maxlen, approximate=True))

        logger.info(f"Trimmed stream {stream} to maxlen {maxlen}")
    except Exception as e:
        logger.warning(f"Failed to trim stream {stream}: {e}")


async def cleanup_old_streams(
    redis_client, pattern: str = "chat:*:stream", maxlen: int = 1000
) -> int:
    """Cleanup old streams by trimming them to maxlen entries."""
    try:
        # Support both async and sync clients
        scan_fn = getattr(redis_client, "scan", None)
        if not scan_fn:
            logger.warning("cleanup_old_streams: scan method not found on redis_client")
            return 0

        scan_method = getattr(type(redis_client), "scan", None)
        cursor = 0
        trimmed = 0

        while True:
            if inspect.iscoroutinefunction(scan_method):
                cursor, keys = await scan_fn(cursor, match=pattern, count=100)
            else:
                cursor, keys = await asyncio.to_thread(
                    lambda current_cursor=cursor: scan_fn(current_cursor, match=pattern, count=100)
                )

            for key in keys:
                try:
                    await trim_stream(redis_client, key, maxlen=maxlen)
                    trimmed += 1
                except Exception as e:
                    logger.warning(f"Failed to trim stream {key}: {e}")

            if cursor == 0:
                break

        logger.info(f"Cleanup completed: trimmed {trimmed} streams")
        return trimmed
    except Exception as e:
        logger.exception(f"Failed to cleanup old streams: {e}")
        return 0
