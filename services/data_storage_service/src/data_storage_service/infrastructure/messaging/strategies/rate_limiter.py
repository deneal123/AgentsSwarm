"""
Rate Limiter implementation.

Provides rate limiting functionality to prevent resource exhaustion
and protect services from overload using token bucket or sliding window algorithms.
"""

import asyncio
import logging
import time
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    pass


class RateLimiter:
    """
    Token bucket rate limiter implementation.

    Controls the rate of operations by maintaining a bucket of tokens
    that are consumed by each operation and refilled over time.

    Example:
        limiter = RateLimiter(max_calls=100, time_window=60)

        async with limiter:
            # Rate-limited operation
            await call_api()
    """

    def __init__(
        self,
        max_calls: int = 100,
        time_window: int = 60,
        strategy: str = "sliding_window",
        name: Optional[str] = None,
    ):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds
            strategy: "token_bucket" or "sliding_window"
            name: Optional name for logging
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.strategy = strategy
        self.name = name or "RateLimiter"

        # Token bucket state
        self._tokens = max_calls
        self._last_refill = time.time()
        self._lock = asyncio.Lock()

        # Sliding window state
        self._call_times: deque = deque()

        logger.info(
            f"{self.name} initialized: {max_calls} calls per {time_window}s "
            f"(strategy: {strategy})"
        )

    @property
    def available_tokens(self) -> int:
        """Get number of available tokens."""
        if self.strategy == "token_bucket":
            self._refill_tokens()
            return int(self._tokens)
        else:
            self._cleanup_old_calls()
            return self.max_calls - len(self._call_times)

    def _refill_tokens(self):
        """Refill tokens based on elapsed time (token bucket)."""
        now = time.time()
        elapsed = now - self._last_refill

        # Calculate tokens to add
        refill_rate = self.max_calls / self.time_window
        tokens_to_add = elapsed * refill_rate

        # Add tokens (up to max)
        self._tokens = min(self.max_calls, self._tokens + tokens_to_add)
        self._last_refill = now

    def _cleanup_old_calls(self):
        """Remove calls outside time window (sliding window)."""
        now = time.time()
        cutoff = now - self.time_window

        while self._call_times and self._call_times[0] < cutoff:
            self._call_times.popleft()

    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens (async).

        Args:
            tokens: Number of tokens to acquire

        Returns:
            bool: True if acquired, False if rate limit exceeded

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        async with self._lock:
            if self.strategy == "token_bucket":
                self._refill_tokens()

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    logger.debug(
                        f"{self.name}: Acquired {tokens} token(s), {self._tokens:.1f} remaining"
                    )
                    return True
                else:
                    logger.warning(
                        f"{self.name}: Rate limit exceeded "
                        f"(requested: {tokens}, available: {self._tokens:.1f})"
                    )
                    raise RateLimitExceeded(
                        f"Rate limit exceeded: {self.max_calls} calls per {self.time_window}s"
                    )

            else:  # sliding_window
                self._cleanup_old_calls()

                if len(self._call_times) < self.max_calls:
                    self._call_times.append(time.time())
                    logger.debug(
                        f"{self.name}: Call recorded, "
                        f"{self.max_calls - len(self._call_times)} slots remaining"
                    )
                    return True
                else:
                    oldest_call = self._call_times[0]
                    wait_time = oldest_call + self.time_window - time.time()
                    logger.warning(
                        f"{self.name}: Rate limit exceeded " f"(retry in {wait_time:.1f}s)"
                    )
                    raise RateLimitExceeded(
                        f"Rate limit exceeded: {self.max_calls} calls per {self.time_window}s "
                        f"(retry in {wait_time:.1f}s)"
                    )

    def acquire_sync(self, tokens: int = 1) -> bool:
        """
        Acquire tokens (sync version).

        Args:
            tokens: Number of tokens to acquire

        Returns:
            bool: True if acquired

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        if self.strategy == "token_bucket":
            self._refill_tokens()

            if self._tokens >= tokens:
                self._tokens -= tokens
                logger.debug(
                    f"{self.name}: Acquired {tokens} token(s), {self._tokens:.1f} remaining"
                )
                return True
            else:
                logger.warning(
                    f"{self.name}: Rate limit exceeded "
                    f"(requested: {tokens}, available: {self._tokens:.1f})"
                )
                raise RateLimitExceeded(
                    f"Rate limit exceeded: {self.max_calls} calls per {self.time_window}s"
                )

        else:  # sliding_window
            self._cleanup_old_calls()

            if len(self._call_times) < self.max_calls:
                self._call_times.append(time.time())
                logger.debug(
                    f"{self.name}: Call recorded, "
                    f"{self.max_calls - len(self._call_times)} slots remaining"
                )
                return True
            else:
                oldest_call = self._call_times[0]
                wait_time = oldest_call + self.time_window - time.time()
                logger.warning(f"{self.name}: Rate limit exceeded " f"(retry in {wait_time:.1f}s)")
                raise RateLimitExceeded(
                    f"Rate limit exceeded: {self.max_calls} calls per {self.time_window}s "
                    f"(retry in {wait_time:.1f}s)"
                )

    async def release(self, tokens: int = 1):
        """
        Release tokens back to bucket (only for token_bucket).

        Args:
            tokens: Number of tokens to release
        """
        if self.strategy != "token_bucket":
            logger.warning(f"{self.name}: release() only works with token_bucket strategy")
            return

        async with self._lock:
            self._tokens = min(self.max_calls, self._tokens + tokens)
            logger.debug(f"{self.name}: Released {tokens} token(s), {self._tokens:.1f} available")

    async def wait_for_token(self, tokens: int = 1, timeout: Optional[float] = None):
        """
        Wait until tokens become available (async).

        Args:
            tokens: Number of tokens needed
            timeout: Maximum time to wait (seconds)

        Raises:
            TimeoutError: If timeout is exceeded
        """
        start_time = time.time()

        while True:
            try:
                await self.acquire(tokens)
                return
            except RateLimitExceeded:
                if timeout and (time.time() - start_time) >= timeout:
                    raise TimeoutError(f"Timeout waiting for rate limit tokens")

                # Wait a bit before retrying
                await asyncio.sleep(0.1)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Tokens are consumed on acquire, no release needed for sliding window
        pass

    def reset(self):
        """Reset rate limiter to initial state."""
        logger.info(f"{self.name}: Resetting rate limiter")
        self._tokens = self.max_calls
        self._last_refill = time.time()
        self._call_times.clear()

    def get_stats(self) -> dict:
        """
        Get rate limiter statistics.

        Returns:
            dict: Statistics including available tokens, call count, etc.
        """
        if self.strategy == "token_bucket":
            self._refill_tokens()
            return {
                "name": self.name,
                "strategy": self.strategy,
                "max_calls": self.max_calls,
                "time_window": self.time_window,
                "available_tokens": int(self._tokens),
                "refill_rate": self.max_calls / self.time_window,
            }
        else:
            self._cleanup_old_calls()
            return {
                "name": self.name,
                "strategy": self.strategy,
                "max_calls": self.max_calls,
                "time_window": self.time_window,
                "current_calls": len(self._call_times),
                "available_slots": self.max_calls - len(self._call_times),
            }
