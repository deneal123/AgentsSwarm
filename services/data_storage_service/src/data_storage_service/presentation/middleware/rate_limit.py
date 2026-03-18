"""Rate limiting middleware using Redis."""

import logging
import time
from typing import Callable, Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from cachetools import TTLCache

    CACHETOOLS_AVAILABLE = True
except ImportError:
    CACHETOOLS_AVAILABLE = False
    TTLCache = None

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with Redis backend and in-memory fallback.

    Uses sliding window algorithm with Redis sorted sets for distributed rate limiting.
    Falls back to TTLCache (or basic dict) when Redis is unavailable.
    """

    def __init__(
        self,
        app,
        redis_client: Optional[Redis] = None,
        redis_getter: Optional[Callable[[], Optional[Redis]]] = None,
        requests_per_minute: int = 60,
        burst_limit: int = 10,
        exempt_paths: Optional[set] = None,
    ):
        super().__init__(app)
        # Support lazy getter so the client can be resolved after container.build()
        self._redis_getter = redis_getter
        self._redis_explicit = redis_client
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.exempt_paths = exempt_paths or {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
        }

        # Initialize in-memory cache as fallback
        if CACHETOOLS_AVAILABLE:
            self._memory_cache = TTLCache(maxsize=10000, ttl=60)
            logger.info(
                "Rate limiting: Initialized with TTLCache fallback (Redis: %s)",
                "enabled" if (redis_client or redis_getter) else "disabled",
            )
        else:
            self._memory_cache = {}
            logger.warning("Rate limiting: cachetools not available, using basic dict fallback")

    @property
    def redis(self) -> Optional[Redis]:
        """Lazily resolve Redis client on first use."""
        if self._redis_explicit is not None:
            return self._redis_explicit
        if self._redis_getter is not None:
            try:
                client = self._redis_getter()
                if client is not None:
                    # Cache the resolved client to avoid repeated lookups
                    self._redis_explicit = client
                return client
            except Exception:
                return None
        return None

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Get client identifier (IP address)
        client_ip = self._get_client_ip(request)

        if self.redis:
            # Use Redis for rate limiting
            allowed = await self._check_redis_rate_limit(client_ip)
        else:
            # Fallback to in-memory rate limiting
            allowed = await self._check_memory_rate_limit(client_ip)

        if not allowed:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
            )

        response = await call_next(request)
        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Fall back to direct connection
        return request.client.host if request.client else "unknown"

    async def _check_redis_rate_limit(self, client_ip: str) -> bool:
        """Check rate limit using Redis sorted sets with sliding window algorithm.

        Uses Redis ZSET for efficient sliding window:
        - Score is timestamp
        - Remove entries older than 60 seconds
        - Count remaining entries
        - Add current request if under limit
        """
        try:
            key = f"ratelimit:ip:{client_ip}"
            now = time.time()
            window_start = now - 60  # 60 seconds sliding window

            # Remove old entries (cleanup sliding window)
            await self.redis.zremrangebyscore(key, 0, window_start)

            # Count current requests in window
            request_count = await self.redis.zcard(key)

            if request_count >= self.requests_per_minute:
                logger.warning(
                    "Rate limit exceeded for IP %s: %d requests in last 60s (limit: %d)",
                    client_ip,
                    request_count,
                    self.requests_per_minute,
                )
                return False

            # Add current request with timestamp as score
            await self.redis.zadd(key, {str(now): now})

            # Set TTL to auto-expire the key (cleanup)
            await self.redis.expire(key, 60)

            return True

        except Exception as e:
            logger.error("Redis rate limit error: %s, falling back to memory", e)
            # Fallback to memory-based limiting
            return await self._check_memory_rate_limit(client_ip)

    async def _check_memory_rate_limit(self, client_ip: str) -> bool:
        """Fallback in-memory rate limiting using TTLCache or basic dict."""
        now = time.time()

        if CACHETOOLS_AVAILABLE:
            # Using TTLCache - automatic expiration
            key = f"ratelimit:{client_ip}"

            # Get request timestamps from cache
            requests = self._memory_cache.get(key, [])

            # Filter out old requests (sliding window - last 60 seconds)
            requests = [t for t in requests if t > now - 60]

            # Check limit
            if len(requests) >= self.requests_per_minute:
                return False

            # Add current request
            requests.append(now)
            self._memory_cache[key] = requests

            return True
        else:
            # Basic dict fallback (less efficient, manual cleanup)
            key = f"ratelimit:{client_ip}"

            # Get or create entry
            if key not in self._memory_cache:
                self._memory_cache[key] = []

            requests = self._memory_cache[key]

            # Filter out old requests
            requests = [t for t in requests if t > now - 60]
            self._memory_cache[key] = requests

            # Check limit
            if len(requests) >= self.requests_per_minute:
                return False

            # Add current request
            requests.append(now)

            # Cleanup old keys periodically (basic cache eviction)
            if len(self._memory_cache) > 10000:
                # Remove oldest 10% of keys
                keys_to_remove = list(self._memory_cache.keys())[:1000]
                for k in keys_to_remove:
                    self._memory_cache.pop(k, None)

            return True
