from service.utils.logging_decorators import log_operation  # type: ignore[import]

# ``log_operation`` used to be defined in this module; the implementation has
# been moved to ``service.utils.logging_decorators`` so that it can be used by
# multiple layers of the application (repositories, services, tasks, etc.).
# We still import and expose it here for backward compatibility with existing
# repository code.

"""
Enhanced decorators for repository methods.

Provides advanced functionality like caching, retry logic, performance
monitoring, validation and logging.  The logging decorator is now shared
between repositories and the rest of the system; see the ``service.utils``
package for the canonical implementation.
"""

import asyncio
import json
import logging
import time
from functools import wraps
from typing import Any, Callable, Coroutine, Optional, ParamSpec, TypeVar

from service.repositories.exceptions import RepositoryError, RepositoryOperationalError
from service.utils.logger import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

# Global Redis cache instance (set by container)
_redis_cache = None


def set_redis_cache(redis_cache) -> None:
    """Set the global Redis cache instance."""
    global _redis_cache
    _redis_cache = redis_cache


def get_redis_cache():
    """Get the global Redis cache instance.
    
    Returns None if the Redis client's event loop is already closed
    (e.g., inside a Celery worker running asyncio.run()).
    """
    if _redis_cache is None:
        return None
    # Guard: if the underlying Redis client was bound to a now-closed event loop,
    # return None so the cache decorator falls back to in-memory only.
    try:
        client = getattr(_redis_cache, "_client", None)
        if client is not None:
            connection_pool = getattr(client, "connection_pool", None)
            if connection_pool is not None:
                loop = getattr(connection_pool, "_loop", None) or getattr(connection_pool, "loop", None)
                if loop is not None and loop.is_closed():
                    return None
    except Exception:
        pass
    return _redis_cache


# ==================== RETRY DECORATOR ====================


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (RepositoryOperationalError,),
) -> Callable[[Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]]:
    """
    Retry decorator for handling transient database errors.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each attempt
        exceptions: Tuple of exception types to catch and retry

    Example:
        @retry(max_attempts=3, delay=1.0, backoff=2.0)
        @connection()
        async def get_user(self, session, user_id):
            ...
    """

    def decorator(func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_exception: Optional[Exception] = None
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if attempt == max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts: {exc}"
                        )
                        break

                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt}/{max_attempts}), "
                        f"retrying in {current_delay}s: {exc}"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            # If we get here, all retries failed
            raise RepositoryError(
                f"Operation failed after {max_attempts} attempts"
            ) from last_exception

        return wrapper

    return decorator


# ==================== VALIDATION DECORATOR ====================


def validate_params(
    **validators: Callable[[Any], bool],
) -> Callable[[Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]]:
    """
    Validate method parameters before execution.

    Args:
        **validators: Mapping of parameter names to validation functions

    Example:
        @validate_params(
            page=lambda x: x > 0,
            page_size=lambda x: 1 <= x <= 100
        )
        @connection()
        async def paginate(self, session, page, page_size):
            ...
    """

    def decorator(func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Validate kwargs
            for param_name, validator in validators.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    if not validator(value):
                        raise ValueError(
                            f"Validation failed for parameter '{param_name}' with value {value}"
                        )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ==================== CACHE DECORATOR (Redis + Fallback) ====================


_memory_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 300.0  # 5 minutes default TTL


def cache(
    ttl: float = _CACHE_TTL,
    namespace: str = "repo",
    key_builder: Optional[Callable[..., str]] = None,
    use_redis: bool = True,
) -> Callable[[Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]]:
    """
    Redis-based cache decorator with in-memory fallback.

    Args:
        ttl: Time-to-live for cache entries (seconds)
        namespace: Redis namespace for keys (default: "repo")
        key_builder: Optional function to build cache key from args/kwargs
        use_redis: Use Redis if available, fallback to in-memory (default: True)

    Example:
        @cache(ttl=60.0, namespace="users")
        @connection()
        async def get_user_by_id(self, session, user_id):
            ...

    Note:
        Uses Redis when available via RedisCacheService.
        Falls back to in-memory cache if Redis is unavailable.
    """

    def decorator(func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Build cache key identifier
            if key_builder:
                identifier = key_builder(*args, **kwargs)
            else:
                # Default key: args (skip self and session)
                args_list = []
                for i, arg in enumerate(args):
                    if i == 0:  # skip self
                        continue
                    args_list.append(str(arg))

                kwargs_list = [f"{k}={v}" for k, v in sorted(kwargs.items()) if k != "session"]

                identifier = f"{func.__name__}:{':'.join(args_list)}:{':'.join(kwargs_list)}"

            # Try Redis first if enabled
            redis_cache = get_redis_cache() if use_redis else None

            if redis_cache:
                try:
                    # Check Redis cache
                    cached_data = await redis_cache.get_json(namespace, identifier)
                    if cached_data is not None:
                        value = cached_data.get("value")
                        # Guard: if cached value is a plain string but looks like a
                        # stringified SQLAlchemy repr, treat as a cache miss and purge it.
                        if isinstance(value, str) and (
                            " object at 0x" in value or value.startswith("<")
                        ):
                            logger.warning(
                                f"Stale SQLAlchemy repr in Redis cache for {func.__name__}:{identifier}; purging"
                            )
                            await redis_cache.invalidate(namespace, identifier)
                        else:
                            logger.debug(f"Redis cache hit for {func.__name__}: {identifier}")
                            return value
                except Exception as exc:
                    logger.warning(f"Redis cache read failed, using in-memory: {exc}")

            # Fallback to in-memory cache
            cache_key = f"{namespace}:{identifier}"
            current_time = time.time()

            if cache_key in _memory_cache:
                cached_time, cached_value = _memory_cache[cache_key]
                if current_time - cached_time < ttl:
                    logger.debug(f"Memory cache hit for {func.__name__}: {cache_key}")
                    return cached_value
                else:
                    # Cache expired
                    del _memory_cache[cache_key]
                    logger.debug(f"Cache expired for {func.__name__}: {cache_key}")

            # Cache miss - execute function
            logger.debug(f"Cache miss for {func.__name__}: {cache_key}")
            result = await func(*args, **kwargs)

            if result is None:
                return result

            # Store in Redis if available (only for JSON-serializable results, not SQLAlchemy models)
            def _is_sqlalchemy_model(obj) -> bool:
                """Check if object is a SQLAlchemy model instance."""
                if obj is None:
                    return False
                if hasattr(obj, "_sa_instance_state"):
                    return True
                if isinstance(obj, list) and obj and hasattr(obj[0], "_sa_instance_state"):
                    return True
                return False

            if redis_cache and not _is_sqlalchemy_model(result):
                try:
                    await redis_cache.set_json(
                        namespace, identifier, {"value": result}, ttl_seconds=int(ttl)
                    )
                    logger.debug(f"Stored in Redis cache: {namespace}:{identifier}")
                except Exception as exc:
                    logger.warning(f"Redis cache write failed: {exc}")

            # Always store in memory cache as fallback
            _memory_cache[cache_key] = (current_time, result)

            return result

        return wrapper

    return decorator


async def clear_cache(namespace: Optional[str] = None) -> None:
    """
    Clear cached values.

    Args:
        namespace: If provided, only clear specific namespace in memory cache.
                  Redis cache requires manual invalidation via RedisCacheService.
    """
    if namespace:
        # Clear specific namespace from memory cache
        keys_to_delete = [k for k in _memory_cache if k.startswith(f"{namespace}:")]
        for key in keys_to_delete:
            del _memory_cache[key]
        logger.info(f"Cleared cache for namespace: {namespace}")
    else:
        # Clear all memory cache
        _memory_cache.clear()
        logger.info("All repository cache cleared")


def get_cache_stats() -> dict[str, Any]:
    """Get cache statistics for in-memory cache."""
    current_time = time.time()
    valid_entries = sum(
        1 for cached_time, _ in _memory_cache.values() if current_time - cached_time < _CACHE_TTL
    )

    return {
        "backend": "redis + memory",
        "redis_available": get_redis_cache() is not None,
        "memory_total_entries": len(_memory_cache),
        "memory_valid_entries": valid_entries,
        "memory_expired_entries": len(_memory_cache) - valid_entries,
    }
