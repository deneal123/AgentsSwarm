"""
Circuit Breaker pattern implementation.

Protects services from cascading failures by monitoring failures
and temporarily blocking requests when threshold is exceeded.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Threshold exceeded, requests fail fast
- HALF_OPEN: Testing if service recovered, limited requests allowed
"""

import logging
import time
from enum import Enum
from typing import Any, Callable, Optional, Type

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance.

    Monitors failures and opens circuit when threshold is exceeded,
    preventing cascading failures. Automatically attempts recovery
    after timeout period.

    Example:
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=RequestException,
        )

        @breaker
        async def call_external_api():
            # API call that might fail
            pass
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception,
        half_open_max_calls: int = 1,
        name: Optional[str] = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds before attempting recovery (HALF_OPEN)
            expected_exception: Exception type to catch
            half_open_max_calls: Max calls allowed in HALF_OPEN state
            name: Optional name for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.half_open_max_calls = half_open_max_calls
        self.name = name or "CircuitBreaker"

        # State tracking
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

        logger.info(
            f"{self.name} initialized: threshold={failure_threshold}, "
            f"timeout={recovery_timeout}s"
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self._state == CircuitState.HALF_OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._last_failure_time is None:
            return True

        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.recovery_timeout

    def _transition_to_half_open(self):
        """Transition from OPEN to HALF_OPEN state."""
        logger.info(f"{self.name}: Transitioning to HALF_OPEN state")
        self._state = CircuitState.HALF_OPEN
        self._half_open_calls = 0

    def _transition_to_open(self):
        """Transition to OPEN state (circuit breaker trips)."""
        logger.warning(
            f"{self.name}: Circuit breaker OPEN "
            f"(failures: {self._failure_count}/{self.failure_threshold})"
        )
        self._state = CircuitState.OPEN
        self._last_failure_time = time.time()

    def _transition_to_closed(self):
        """Transition to CLOSED state (normal operation resumed)."""
        logger.info(f"{self.name}: Circuit breaker CLOSED (recovered)")
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0

    def _record_success(self):
        """Record successful call."""
        if self._state == CircuitState.HALF_OPEN:
            # Success in HALF_OPEN means we can close the circuit
            self._transition_to_closed()
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            if self._failure_count > 0:
                self._failure_count = 0

    def _record_failure(self):
        """Record failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Failure in HALF_OPEN means service still broken
            logger.warning(f"{self.name}: Recovery failed, reopening circuit")
            self._transition_to_open()

        elif self._state == CircuitState.CLOSED:
            # Check if we've hit the threshold
            if self._failure_count >= self.failure_threshold:
                self._transition_to_open()
            else:
                logger.debug(
                    f"{self.name}: Failure recorded "
                    f"({self._failure_count}/{self.failure_threshold})"
                )

    def _check_state(self):
        """Check and update state before call."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise CircuitBreakerError(
                    f"{self.name}: Circuit breaker is OPEN "
                    f"(recovery in {self.recovery_timeout - (time.time() - self._last_failure_time):.0f}s)"
                )

        elif self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerError(f"{self.name}: Too many calls in HALF_OPEN state")
            self._half_open_calls += 1

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker (sync).

        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
        """
        self._check_state()

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result

        except self.expected_exception as e:
            self._record_failure()
            raise

        except Exception as e:
            # Unexpected exception, don't count as failure
            logger.exception(f"{self.name}: Unexpected exception: {e}")
            raise

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute async function through circuit breaker.

        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
        """
        self._check_state()

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result

        except self.expected_exception as e:
            self._record_failure()
            raise

        except Exception as e:
            # Unexpected exception, don't count as failure
            logger.exception(f"{self.name}: Unexpected exception: {e}")
            raise

    def __call__(self, func: Callable) -> Callable:
        """
        Decorator for wrapping functions with circuit breaker.

        Example:
            @circuit_breaker
            def my_function():
                pass
        """
        if hasattr(func, "__call__") and hasattr(func, "__await__"):
            # Async function
            async def async_wrapper(*args, **kwargs):
                return await self.call_async(func, *args, **kwargs)

            return async_wrapper
        else:
            # Sync function
            def sync_wrapper(*args, **kwargs):
                return self.call(func, *args, **kwargs)

            return sync_wrapper

    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        logger.info(f"{self.name}: Manually resetting circuit breaker")
        self._transition_to_closed()

    def get_stats(self) -> dict:
        """
        Get circuit breaker statistics.

        Returns:
            dict: Statistics including state, failure count, etc.
        """
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self._last_failure_time,
            "recovery_timeout": self.recovery_timeout,
            "is_open": self.is_open,
            "is_half_open": self.is_half_open,
            "is_closed": self.is_closed,
        }
