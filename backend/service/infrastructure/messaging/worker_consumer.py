import asyncio
from collections.abc import Callable
from typing import Any


async def consume_once(
    redis_client,
    stream: str,
    group: str,
    consumer: str,
    process_func: Callable[[str, dict[str, Any]], Any],
    count: int = 1,
    timeout: int = 1000,
):
    """Read up to `count` messages from `stream` consumer group and process them once.

    Expected redis_client API: xread_group(group, consumer, streams={stream: '>'}, count=count, timeout=timeout)
    process_func should be an async callable taking (message_id, mapping) and returning truthy if processed.
    On successful processing the message will be XACKed.
    Returns number of processed messages.
    """
    # call redis xread_group
    records = await redis_client.xread_group(
        group=group,
        consumer=consumer,
        streams={stream: ">"},
        count=count,
        timeout=timeout,
    )
    processed = 0
    # records expected format: [(stream_key, [(id, {k: v}), ...])]
    for _stream_key, messages in records:
        for message_id, mapping in messages:
            try:
                ok = await process_func(message_id, mapping)
                if ok:
                    await redis_client.xack(stream, group, message_id)
                    processed += 1
            except Exception:
                # do not ack on exception; let pending mechanism handle it
                continue
    return processed


async def consume_loop(
    redis_client,
    stream: str,
    group: str,
    consumer: str,
    process_func: Callable[[str, dict[str, Any]], Any],
    poll_interval: float = 0.5,
):
    """Run consume_once in a loop until cancelled.

    This is a simple worker loop suitable for examples and tests.
    """
    try:
        while True:
            processed = await consume_once(
                redis_client,
                stream,
                group,
                consumer,
                process_func,
            )
            if processed == 0:
                await asyncio.sleep(poll_interval)
    except asyncio.CancelledError:
        return


async def reclaim_pending(
    redis_client,
    stream: str,
    group: str,
    consumer: str,
    min_idle_ms: int = 60000,
    count: int = 10,
):
    """Attempt to claim pending messages that are idle longer than min_idle_ms.

    Uses XAUTOCLAIM/XAUTOCLAIM-like interface. Returns list of claimed (id, mapping).
    """
    # Some redis clients expose different names; try both
    if hasattr(redis_client, "xauto_claim"):
        res = await redis_client.xauto_claim(
            stream,
            group,
            consumer,
            min_idle_ms,
            "0-0",
            count=count,
        )
    elif hasattr(redis_client, "xautoclaim"):
        res = await redis_client.xautoclaim(
            stream,
            group,
            consumer,
            min_idle_ms,
            "0-0",
            count=count,
        )
    else:
        return []

    # res expected to be list of (id, mapping) or tuple(description)
    return res
