"""
Examples of using Circuit Breaker and Rate Limiter.

Demonstrates practical usage patterns for fault tolerance
and rate limiting in production scenarios.
"""

import asyncio
import logging
from typing import Optional

from service.infrastructure.messaging.strategies import (
    CircuitBreaker,
    CircuitBreakerError,
    RateLimiter,
    RateLimitExceeded,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Circuit Breaker Examples
# ============================================================================


class ExternalAPIError(Exception):
    """Custom exception for API failures."""

    pass


# Example 1: Decorator pattern
circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30,
    expected_exception=ExternalAPIError,
    name="ExternalAPI",
)


@circuit_breaker
async def call_external_api(data: dict) -> dict:
    """
    Protected API call with circuit breaker.

    Circuit breaker will open after 3 failures and block
    requests for 30 seconds before attempting recovery.
    """
    # Simulate API call
    logger.info(f"Calling external API with data: {data}")

    # If this raises ExternalAPIError, it will be counted
    # as a failure by the circuit breaker
    if data.get("should_fail"):
        raise ExternalAPIError("API is down")

    return {"success": True, "data": data}


# Example 2: Explicit call pattern
async def call_payment_gateway(amount: float) -> dict:
    """Call payment gateway (unprotected)."""
    logger.info(f"Processing payment: ${amount}")

    # Simulate occasional failures
    import random

    if random.random() < 0.3:  # 30% failure rate
        raise ExternalAPIError("Payment gateway timeout")

    return {"transaction_id": "12345", "status": "success"}


async def process_payment_with_circuit_breaker(amount: float) -> Optional[dict]:
    """Process payment protected by circuit breaker."""
    breaker = CircuitBreaker(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=ExternalAPIError,
        name="PaymentGateway",
    )

    try:
        result = await breaker.call_async(call_payment_gateway, amount)
        logger.info(f"Payment successful: {result}")
        return result

    except CircuitBreakerError as e:
        logger.error(f"Circuit breaker is open: {e}")
        # Handle gracefully - maybe queue for later
        return None

    except ExternalAPIError as e:
        logger.error(f"Payment failed: {e}")
        return None


# Example 3: Manual state management
async def check_service_health() -> bool:
    """Check if external service is healthy."""
    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=10,
        name="HealthCheck",
    )

    stats = breaker.get_stats()
    logger.info(f"Circuit breaker stats: {stats}")

    if breaker.is_open:
        logger.warning("Service is unavailable (circuit open)")
        return False

    # Manually reset circuit if needed
    # breaker.reset()

    return breaker.is_closed


# ============================================================================
# Rate Limiter Examples
# ============================================================================


# Example 1: Context manager pattern (async)
async def send_emails_with_rate_limit(emails: list[str]):
    """
    Send emails with rate limiting.

    Limits to 100 emails per minute to avoid overwhelming
    the email service.
    """
    limiter = RateLimiter(
        max_calls=100,
        time_window=60,
        strategy="sliding_window",
        name="EmailService",
    )

    for email in emails:
        try:
            async with limiter:
                # Rate-limited operation
                logger.info(f"Sending email to {email}")
                await asyncio.sleep(0.1)  # Simulate sending

        except RateLimitExceeded as e:
            logger.warning(f"Rate limit exceeded: {e}")
            # Wait and retry or handle gracefully
            await asyncio.sleep(1)


# Example 2: Token bucket with explicit acquire
async def process_api_requests(requests: list[dict]):
    """
    Process API requests with token bucket rate limiter.

    Allows bursts up to 50 requests, then throttles to
    average rate of 10 requests per second.
    """
    limiter = RateLimiter(
        max_calls=50,
        time_window=5,  # 50 calls per 5 seconds = 10/sec
        strategy="token_bucket",
        name="APIRequests",
    )

    for request in requests:
        try:
            # Acquire token
            await limiter.acquire()

            # Process request
            logger.info(f"Processing request: {request['id']}")
            await asyncio.sleep(0.05)

        except RateLimitExceeded:
            # Wait for token to become available
            logger.warning("Rate limit exceeded, waiting...")
            await limiter.wait_for_token(timeout=10)

            # Retry
            await limiter.acquire()
            logger.info(f"Processing request (retried): {request['id']}")


# Example 3: Multiple rate limiters (tiered)
class APIClient:
    """
    API client with tiered rate limiting.

    Implements both per-user and global rate limits.
    """

    def __init__(self):
        # Global rate limit: 1000 requests per minute
        self.global_limiter = RateLimiter(
            max_calls=1000,
            time_window=60,
            strategy="token_bucket",
            name="GlobalAPI",
        )

        # Per-user rate limit: 100 requests per minute
        self.user_limiters = {}

    def _get_user_limiter(self, user_id: str) -> RateLimiter:
        """Get or create rate limiter for user."""
        if user_id not in self.user_limiters:
            self.user_limiters[user_id] = RateLimiter(
                max_calls=100,
                time_window=60,
                strategy="sliding_window",
                name=f"User_{user_id}",
            )
        return self.user_limiters[user_id]

    async def make_request(self, user_id: str, endpoint: str) -> dict:
        """
        Make API request with tiered rate limiting.

        Must pass both global and per-user rate limits.
        """
        user_limiter = self._get_user_limiter(user_id)

        try:
            # Check global limit first
            await self.global_limiter.acquire()

            # Then check user limit
            await user_limiter.acquire()

            # Make request
            logger.info(f"User {user_id} calling {endpoint}")
            return {"success": True}

        except RateLimitExceeded as e:
            logger.error(f"Rate limit exceeded for user {user_id}: {e}")
            raise

    def get_stats(self, user_id: Optional[str] = None) -> dict:
        """Get rate limiter statistics."""
        stats = {
            "global": self.global_limiter.get_stats(),
        }

        if user_id:
            limiter = self._get_user_limiter(user_id)
            stats["user"] = limiter.get_stats()

        return stats


# ============================================================================
# Combined Example: Circuit Breaker + Rate Limiter
# ============================================================================


class ResilientAPIClient:
    """
    API client with both circuit breaker and rate limiter.

    Provides comprehensive protection against:
    - Service failures (circuit breaker)
    - Rate limit violations (rate limiter)
    """

    def __init__(self):
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=ExternalAPIError,
            name="ResilientAPI",
        )

        self.rate_limiter = RateLimiter(
            max_calls=100,
            time_window=60,
            strategy="token_bucket",
            name="ResilientAPI",
        )

    async def call_api(self, endpoint: str, data: dict) -> Optional[dict]:
        """
        Make API call with full protection.

        Flow:
        1. Check rate limit first (fail fast)
        2. Check circuit breaker state
        3. Make actual API call
        4. Record success/failure
        """
        try:
            # Rate limit check
            await self.rate_limiter.acquire()

            # Circuit breaker protection
            async def _make_call():
                logger.info(f"Calling {endpoint}")
                # Simulate API call
                await asyncio.sleep(0.1)
                return {"status": "success"}

            result = await self.circuit_breaker.call_async(_make_call)
            return result

        except RateLimitExceeded as e:
            logger.warning(f"Rate limit exceeded: {e}")
            return None

        except CircuitBreakerError as e:
            logger.error(f"Circuit breaker open: {e}")
            return None

        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return None

    def get_health_status(self) -> dict:
        """Get combined health status."""
        return {
            "circuit_breaker": self.circuit_breaker.get_stats(),
            "rate_limiter": self.rate_limiter.get_stats(),
            "healthy": (self.circuit_breaker.is_closed and self.rate_limiter.available_tokens > 0),
        }


# ============================================================================
# Demo Runner
# ============================================================================


async def main():
    """Run all examples."""
    logger.info("=" * 70)
    logger.info("Circuit Breaker & Rate Limiter Examples")
    logger.info("=" * 70)

    # Example 1: Circuit breaker decorator
    logger.info("\n1. Circuit Breaker Decorator Pattern")
    try:
        result = await call_external_api({"test": "data"})
        logger.info(f"Result: {result}")
    except Exception as e:
        logger.error(f"Error: {e}")

    # Example 2: Rate limiter context manager
    logger.info("\n2. Rate Limiter Context Manager")
    await send_emails_with_rate_limit(["user1@example.com", "user2@example.com"])

    # Example 3: Combined protection
    logger.info("\n3. Combined Circuit Breaker + Rate Limiter")
    client = ResilientAPIClient()
    for i in range(5):
        result = await client.call_api("/test", {"request": i})
        logger.info(f"Request {i}: {result}")

    logger.info(f"\nHealth Status: {client.get_health_status()}")

    logger.info("\n" + "=" * 70)
    logger.info("Examples completed!")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
