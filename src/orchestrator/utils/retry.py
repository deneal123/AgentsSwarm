"""Retry utilities for transient MCP/network operations.

Includes sync and async helpers with exponential backoff and jitter.
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")


def _compute_backoff(base: float, factor: float, attempt: int, jitter: float) -> float:
    delay = base * (factor ** max(attempt - 1, 0))
    if jitter:
        delay += random.uniform(0, jitter)
    return delay


def retry_sync(
    func: Callable[..., T],
    *args: Any,
    retries: int = 3,
    base_delay: float = 0.1,
    factor: float = 2.0,
    jitter: float = 0.05,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    **kwargs: Any,
) -> T:
    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)
        except exceptions:
            if attempt >= retries:
                raise
            delay = _compute_backoff(base_delay, factor, attempt, jitter)
            time.sleep(delay)
    raise RuntimeError("retry_sync exhausted")


async def retry_async(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    retries: int = 3,
    base_delay: float = 0.1,
    factor: float = 2.0,
    jitter: float = 0.05,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    **kwargs: Any,
) -> T:
    for attempt in range(1, retries + 1):
        try:
            return await func(*args, **kwargs)
        except exceptions:
            if attempt >= retries:
                raise
            delay = _compute_backoff(base_delay, factor, attempt, jitter)
            await asyncio.sleep(delay)
    raise RuntimeError("retry_async exhausted")


__all__ = ["retry_async", "retry_sync"]
