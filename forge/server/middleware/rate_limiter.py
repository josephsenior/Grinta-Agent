"""Rate limiting middleware for Forge API."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING, Callable

from fastapi.responses import JSONResponse

from forge.core.logger import forge_logger as logger

if TYPE_CHECKING:
    from fastapi import Request, Response

# In-memory rate limit store (use Redis in production for distributed systems)
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


class RateLimiter:
    """Rate limiting middleware for API endpoints."""

    def __init__(
        self,
        requests_per_hour: int = 100,
        burst_limit: int = 20,
        enabled: bool = True,
    ) -> None:
        """Initialize rate limiter.

        Args:
            requests_per_hour: Maximum requests allowed per hour
            burst_limit: Maximum requests allowed in a 1-minute window
            enabled: Whether rate limiting is enabled

        """
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        self.enabled = enabled
        self.hour_window = 3600  # 1 hour in seconds
        self.burst_window = 60  # 1 minute in seconds

    async def __call__(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request with rate limiting.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response or rate limit error

        """
        if not self.enabled:
            return await call_next(request)

        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/api/health", "/"] or request.url.path.startswith("/assets"):
            return await call_next(request)

        # Get rate limit key (user_id or IP address)
        rate_limit_key = await self._get_rate_limit_key(request)

        # Check rate limits
        if not await self._check_rate_limit(rate_limit_key):
            logger.warning(f"Rate limit exceeded for {rate_limit_key}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": 60,
                },
                headers={"Retry-After": "60"},
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = await self._get_remaining_requests(rate_limit_key)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + self.hour_window))

        return response

    async def _get_rate_limit_key(self, request: Request) -> str:
        """Get rate limit key from request.

        Tries to use user_id from auth, falls back to IP address.

        Args:
            request: FastAPI request

        Returns:
            Rate limit key (user_id or IP)

        """
        # Try to get user_id from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Use first IP in X-Forwarded-For chain
            client_ip = forwarded_for.split(",")[0].strip()

        return f"ip:{client_ip}"

    async def _check_rate_limit(self, key: str) -> bool:
        """Check if request is within rate limits.

        Args:
            key: Rate limit key

        Returns:
            True if within limits, False if exceeded

        """
        current_time = time.time()

        # Get request timestamps for this key
        timestamps = _rate_limit_store[key]

        # Remove old timestamps (outside the hour window)
        timestamps[:] = [ts for ts in timestamps if current_time - ts < self.hour_window]

        # Check hourly limit
        if len(timestamps) >= self.requests_per_hour:
            return False

        # Check burst limit (requests in last minute)
        recent_requests = [ts for ts in timestamps if current_time - ts < self.burst_window]
        if len(recent_requests) >= self.burst_limit:
            return False

        # Add current request timestamp
        timestamps.append(current_time)

        return True

    async def _get_remaining_requests(self, key: str) -> int:
        """Get remaining requests for key.

        Args:
            key: Rate limit key

        Returns:
            Number of remaining requests in current window

        """
        current_time = time.time()
        timestamps = _rate_limit_store[key]

        # Count requests in current hour
        hour_requests = [ts for ts in timestamps if current_time - ts < self.hour_window]

        return max(0, self.requests_per_hour - len(hour_requests))


# Endpoint-specific rate limiters
class EndpointRateLimiter:
    """Rate limiter with endpoint-specific limits."""

    # Define limits per endpoint pattern
    # 🚀 PRODUCTION FIX: Configurable limits via environment variables
    @staticmethod
    def _get_default_limits():
        """Get default rate limits from environment variables."""
        import os
        requests_per_hour = int(os.getenv("RATE_LIMIT_REQUESTS", "1000"))
        burst_limit = int(os.getenv("RATE_LIMIT_BURST", "100"))
        logger.info(f"Rate limiting configured: {requests_per_hour} req/hour, {burst_limit} burst")
        return requests_per_hour, burst_limit
    
    def __init__(self, enabled: bool = True) -> None:
        """Initialize endpoint-specific rate limiter.

        Args:
            enabled: Whether rate limiting is enabled

        """
        self.enabled = enabled
        # Get default limits from environment variables
        default_limits = self._get_default_limits()
        
        # Define limits per endpoint pattern
        self.LIMITS = {
            "/api/conversations": default_limits,  # Use env-configured limits
            "/api/prompts": default_limits,
            "/api/database": default_limits,
            "/api/memory": default_limits,
            "/api/slack/events": default_limits,
            "/api/monitoring": default_limits,  # ← Add monitoring endpoints
            "default": default_limits,  # Default limits from environment
        }

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request with endpoint-specific rate limiting.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response or rate limit error

        """
        if not self.enabled:
            return await call_next(request)

        # Get endpoint-specific limits
        path = request.url.path
        limits = self._get_limits_for_path(path)
        requests_per_hour, burst_limit = limits

        # Create rate limiter with endpoint-specific limits
        limiter = RateLimiter(
            requests_per_hour=requests_per_hour,
            burst_limit=burst_limit,
            enabled=self.enabled,
        )

        return await limiter(request, call_next)

    def _get_limits_for_path(self, path: str) -> tuple[int, int]:
        """Get rate limits for specific path.

        Args:
            path: Request path

        Returns:
            Tuple of (requests_per_hour, burst_limit)

        """
        for pattern, limits in self.LIMITS.items():
            if pattern in path:
                return limits

        return self.LIMITS["default"]


# Redis-backed rate limiter for production (optional)
try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.debug("Redis not available. Using in-memory rate limiting.")


class RedisRateLimiter(RateLimiter):
    """Redis-backed rate limiter for distributed systems."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        requests_per_hour: int | None = None,  # 🚀 Now reads from env vars
        burst_limit: int | None = None,  # 🚀 Now reads from env vars
        enabled: bool = True,
    ) -> None:
        """Initialize Redis rate limiter.

        Args:
            redis_url: Redis connection URL
            requests_per_hour: Maximum requests allowed per hour (None = use env var)
            burst_limit: Maximum requests allowed in 1-minute window (None = use env var)
            enabled: Whether rate limiting is enabled

        """
        # 🚀 PRODUCTION FIX: Read from environment variables if not provided
        import os
        if requests_per_hour is None:
            requests_per_hour = int(os.getenv("RATE_LIMIT_REQUESTS", "1000"))
        if burst_limit is None:
            burst_limit = int(os.getenv("RATE_LIMIT_BURST", "100"))
        
        logger.info(f"RedisRateLimiter configured: {requests_per_hour} req/hour, {burst_limit} burst")
        super().__init__(requests_per_hour, burst_limit, enabled)
        self.redis_url = redis_url
        self._redis_client: redis.Redis | None = None

    async def _get_redis_client(self) -> redis.Redis | None:
        """Get or create Redis client.

        Returns:
            Redis client or None if unavailable

        """
        if not REDIS_AVAILABLE:
            return None

        if self._redis_client is None:
            try:
                self._redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                )
                # Test connection
                await self._redis_client.ping()
                logger.info("Connected to Redis for rate limiting")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Falling back to in-memory.")
                self._redis_client = None

        return self._redis_client

    async def _check_rate_limit(self, key: str) -> bool:
        """Check rate limit using Redis.

        Args:
            key: Rate limit key

        Returns:
            True if within limits, False if exceeded

        """
        redis_client = await self._get_redis_client()

        # Fall back to in-memory if Redis unavailable
        if redis_client is None:
            return await super()._check_rate_limit(key)

        try:
            current_time = int(time.time())

            # Use Redis sorted set for timestamps
            redis_key = f"ratelimit:{key}"

            # Remove old timestamps
            await redis_client.zremrangebyscore(
                redis_key,
                0,
                current_time - self.hour_window,
            )

            # Count requests in hour window
            hour_count = await redis_client.zcount(
                redis_key,
                current_time - self.hour_window,
                current_time,
            )

            if hour_count >= self.requests_per_hour:
                return False

            # Count requests in burst window
            burst_count = await redis_client.zcount(
                redis_key,
                current_time - self.burst_window,
                current_time,
            )

            if burst_count >= self.burst_limit:
                logger.debug(f"Burst limit exceeded: {burst_count}/{self.burst_limit} for {key}")
                return False

            # Add current request with microsecond precision to avoid deduplication
            # 🔧 FIX: Use microseconds to make each request unique
            import uuid
            unique_id = f"{current_time}:{uuid.uuid4()}"
            await redis_client.zadd(redis_key, {unique_id: current_time})

            # Set expiry
            await redis_client.expire(redis_key, self.hour_window)

            return True

        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}. Allowing request.")
            # Fail open - allow request if Redis fails
            return True

    async def _get_remaining_requests(self, key: str) -> int:
        """Get remaining requests using Redis.

        Args:
            key: Rate limit key

        Returns:
            Number of remaining requests

        """
        redis_client = await self._get_redis_client()

        if redis_client is None:
            return await super()._get_remaining_requests(key)

        try:
            current_time = int(time.time())
            redis_key = f"ratelimit:{key}"

            hour_count = await redis_client.zcount(
                redis_key,
                current_time - self.hour_window,
                current_time,
            )

            return max(0, self.requests_per_hour - hour_count)

        except Exception as e:
            logger.error(f"Redis remaining count failed: {e}")
            return self.requests_per_hour  # Return max if Redis fails
