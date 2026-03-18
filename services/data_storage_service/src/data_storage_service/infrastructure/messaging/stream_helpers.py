"""
Redis Streams helper functions.

Provides high-level wrappers for Redis Streams operations:
- Consumer group management
- Message reading/writing
- Pending entry management
- Stream cleanup
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


async def ensure_group(
    redis_client,
    stream_key: str,
    group: str,
    mkstream: bool = True,
    start_id: str = "$",
) -> bool:
    """
    Ensure consumer group exists for stream.

    Args:
        redis_client: Redis client instance
        stream_key: Redis stream key
        group: Consumer group name
        mkstream: Create stream if it doesn't exist
        start_id: Starting position for group (default: "$" - end of stream)

    Returns:
        bool: True if group was created or already exists
    """
    try:
        await redis_client.xgroup_create(
            name=stream_key,
            groupname=group,
            id=start_id,
            mkstream=mkstream,
        )
        logger.info(f"Created consumer group '{group}' for stream '{stream_key}'")
        return True
    except Exception as e:
        # Group already exists
        if "BUSYGROUP" in str(e):
            logger.debug(f"Consumer group '{group}' already exists for stream '{stream_key}'")
            return True
        logger.error(f"Failed to ensure group '{group}' for stream '{stream_key}': {e}")
        return False


async def xadd(
    redis_client,
    stream_key: str,
    fields: Dict[str, Any],
    maxlen: Optional[int] = None,
    approximate: bool = True,
) -> str:
    """
    Add message to Redis Stream.

    Args:
        redis_client: Redis client instance
        stream_key: Redis stream key
        fields: Message fields (dict)
        maxlen: Maximum stream length (for trimming)
        approximate: Use approximate trimming (~)

    Returns:
        str: Message ID
    """
    try:
        # Convert all values to strings
        string_fields = {k: str(v) if v is not None else "" for k, v in fields.items()}

        kwargs = {"name": stream_key, "fields": string_fields}
        if maxlen:
            kwargs["maxlen"] = maxlen
            kwargs["approximate"] = approximate

        message_id = await redis_client.xadd(**kwargs)
        logger.debug(f"Added message to stream '{stream_key}': {message_id}")
        return message_id
    except Exception as e:
        logger.exception(f"Failed to add message to stream '{stream_key}': {e}")
        raise


async def xread(
    redis_client,
    streams: Dict[str, str],
    count: Optional[int] = None,
    block: Optional[int] = None,
) -> List[Tuple[str, List[Tuple[str, Dict]]]]:
    """
    Read messages from Redis Streams.

    Args:
        redis_client: Redis client instance
        streams: Dict of {stream_key: last_id}
        count: Maximum number of messages per stream
        block: Block for N milliseconds (None = non-blocking)

    Returns:
        List of (stream_key, [(message_id, fields)])
    """
    try:
        kwargs = {"streams": streams}
        if count:
            kwargs["count"] = count
        if block is not None:
            kwargs["block"] = block

        result = await redis_client.xread(**kwargs)
        return result or []
    except Exception as e:
        logger.exception(f"Failed to read from streams: {e}")
        return []


async def xreadgroup(
    redis_client,
    group: str,
    consumer: str,
    streams: Dict[str, str],
    count: Optional[int] = None,
    block: Optional[int] = None,
    noack: bool = False,
) -> List[Tuple[str, List[Tuple[str, Dict]]]]:
    """
    Read messages from Redis Streams using consumer group.

    Args:
        redis_client: Redis client instance
        group: Consumer group name
        consumer: Consumer name
        streams: Dict of {stream_key: last_id} (">" for new messages)
        count: Maximum number of messages
        block: Block for N milliseconds
        noack: Don't add to pending list

    Returns:
        List of (stream_key, [(message_id, fields)])
    """
    try:
        kwargs = {
            "groupname": group,
            "consumername": consumer,
            "streams": streams,
        }
        if count:
            kwargs["count"] = count
        if block is not None:
            kwargs["block"] = block
        if noack:
            kwargs["noack"] = noack

        result = await redis_client.xreadgroup(**kwargs)
        return result or []
    except Exception as e:
        logger.exception(f"Failed to xreadgroup: {e}")
        return []


async def xrange(
    redis_client,
    stream_key: str,
    min_id: str = "-",
    max_id: str = "+",
    count: Optional[int] = None,
) -> List[Tuple[str, Dict]]:
    """
    Get range of messages from stream.

    Args:
        redis_client: Redis client instance
        stream_key: Redis stream key
        min_id: Minimum message ID ("-" for start)
        max_id: Maximum message ID ("+" for end)
        count: Maximum number of messages

    Returns:
        List of (message_id, fields)
    """
    try:
        kwargs = {
            "name": stream_key,
            "min": min_id,
            "max": max_id,
        }
        if count:
            kwargs["count"] = count

        result = await redis_client.xrange(**kwargs)
        return result or []
    except Exception as e:
        logger.exception(f"Failed to xrange on stream '{stream_key}': {e}")
        return []


async def xpending(
    redis_client,
    stream_key: str,
    group: str,
    min_id: str = "-",
    max_id: str = "+",
    count: Optional[int] = None,
    consumer: Optional[str] = None,
) -> List:
    """
    Get pending messages from consumer group.

    Args:
        redis_client: Redis client instance
        stream_key: Redis stream key
        group: Consumer group name
        min_id: Minimum message ID
        max_id: Maximum message ID
        count: Maximum number of messages
        consumer: Specific consumer (optional)

    Returns:
        List of pending message info
    """
    try:
        # First, get summary
        if not count:
            result = await redis_client.xpending(name=stream_key, groupname=group)
            return result

        # Get detailed pending info
        kwargs = {
            "name": stream_key,
            "groupname": group,
            "min": min_id,
            "max": max_id,
            "count": count,
        }
        if consumer:
            kwargs["consumername"] = consumer

        result = await redis_client.xpending_range(**kwargs)
        return result or []
    except Exception as e:
        logger.exception(f"Failed to xpending on stream '{stream_key}': {e}")
        return []


async def xack(
    redis_client,
    stream_key: str,
    group: str,
    *message_ids: str,
) -> int:
    """
    Acknowledge processed messages.

    Args:
        redis_client: Redis client instance
        stream_key: Redis stream key
        group: Consumer group name
        *message_ids: Message IDs to acknowledge

    Returns:
        int: Number of messages acknowledged
    """
    try:
        if not message_ids:
            return 0

        result = await redis_client.xack(
            name=stream_key,
            groupname=group,
            *message_ids,
        )
        logger.debug(f"Acknowledged {result} messages in stream '{stream_key}'")
        return result
    except Exception as e:
        logger.exception(f"Failed to xack messages in stream '{stream_key}': {e}")
        return 0


async def xautoclaim(
    redis_client,
    stream_key: str,
    group: str,
    consumer: str,
    min_idle_time: int,
    start_id: str = "0-0",
    count: Optional[int] = None,
) -> Tuple[str, List[Tuple[str, Dict]]]:
    """
    Auto-claim idle pending messages (Redis 6.2+).

    Args:
        redis_client: Redis client instance
        stream_key: Redis stream key
        group: Consumer group name
        consumer: Consumer name to claim for
        min_idle_time: Minimum idle time in milliseconds
        start_id: Start ID for scanning
        count: Maximum number of messages to claim

    Returns:
        Tuple of (next_start_id, [(message_id, fields)])
    """
    try:
        kwargs = {
            "name": stream_key,
            "groupname": group,
            "consumername": consumer,
            "min_idle_time": min_idle_time,
            "start_id": start_id,
        }
        if count:
            kwargs["count"] = count

        result = await redis_client.xautoclaim(**kwargs)

        # xautoclaim returns (next_id, messages, deleted_ids) in Redis 6.2+
        if isinstance(result, tuple) and len(result) >= 2:
            next_id, messages = result[0], result[1]
            return (next_id, messages or [])

        return ("0-0", [])
    except Exception as e:
        logger.exception(f"Failed to xautoclaim on stream '{stream_key}': {e}")
        return ("0-0", [])


# Alias for compatibility
xauto_claim = xautoclaim


async def xtrim(
    redis_client,
    stream_key: str,
    maxlen: int,
    approximate: bool = True,
) -> int:
    """
    Trim stream to maximum length.

    Args:
        redis_client: Redis client instance
        stream_key: Redis stream key
        maxlen: Maximum length
        approximate: Use approximate trimming (~)

    Returns:
        int: Number of entries deleted
    """
    try:
        result = await redis_client.xtrim(
            name=stream_key,
            maxlen=maxlen,
            approximate=approximate,
        )
        logger.info(f"Trimmed stream '{stream_key}' to {maxlen} entries (deleted {result})")
        return result
    except Exception as e:
        logger.exception(f"Failed to trim stream '{stream_key}': {e}")
        return 0


async def cleanup_old_streams(
    redis_client,
    pattern: str = "*:stream",
    maxlen: int = 1000,
) -> int:
    """
    Cleanup old streams matching pattern.

    Args:
        redis_client: Redis client instance
        pattern: Stream key pattern (e.g., "chat:*:stream")
        maxlen: Maximum length to trim to

    Returns:
        int: Number of streams trimmed
    """
    try:
        # Find matching keys
        keys = []
        async for key in redis_client.scan_iter(match=pattern):
            keys.append(key)

        trimmed_count = 0
        for key in keys:
            result = await xtrim(redis_client, key, maxlen, approximate=True)
            if result > 0:
                trimmed_count += 1

        logger.info(f"Cleaned up {trimmed_count} streams matching pattern '{pattern}'")
        return trimmed_count
    except Exception as e:
        logger.exception(f"Failed to cleanup streams with pattern '{pattern}': {e}")
        return 0
