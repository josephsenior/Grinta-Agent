"""Cost-based quota system for LLM API usage.

Tracks actual $ spent instead of just request counts.
Supports per-user and per-plan quotas (free, pro, enterprise).
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
import os
import random
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Callable

from fastapi.responses import JSONResponse

from backend.core.constants import (
    ENTERPRISE_PLAN_BURST_LIMIT,
    ENTERPRISE_PLAN_DAILY_LIMIT,
    ENTERPRISE_PLAN_MONTHLY_LIMIT,
    FREE_PLAN_BURST_LIMIT,
    FREE_PLAN_DAILY_LIMIT,
    FREE_PLAN_MONTHLY_LIMIT,
    PRO_PLAN_BURST_LIMIT,
    PRO_PLAN_DAILY_LIMIT,
    PRO_PLAN_MONTHLY_LIMIT,
    QUOTA_EXEMPT_PATH_PREFIXES,
    QUOTA_EXEMPT_PATHS,
    DEFAULT_QUOTA_DAY_WINDOW,
    DEFAULT_QUOTA_HOUR_WINDOW,
    DEFAULT_QUOTA_MONTH_WINDOW,
    QuotaPlan,
)
from backend.core.logger import forge_logger as logger, get_trace_context
from backend.server.utils.responses import error

if TYPE_CHECKING:
    from fastapi import Request, Response


# Cost tracking store (use Redis in production for distributed systems)
_cost_store: dict[str, dict[str, float]] = defaultdict(
    lambda: {
        "daily_cost": 0.0,
        "monthly_cost": 0.0,
        "last_reset_day": time.time(),
        "last_reset_month": time.time(),
    }
)





@dataclass
class QuotaConfig:
    """Quota configuration for a plan."""

    plan: QuotaPlan
    daily_limit: float  # $ per day
    monthly_limit: float  # $ per month
    burst_limit: float  # $ per hour


@dataclass(frozen=True)
class RedisQuotaKeys:
    """Helper container for Redis key names used per user."""

    daily: str
    monthly: str
    daily_reset: str
    monthly_reset: str


# Default quota configs
QUOTA_CONFIGS = {
    QuotaPlan.FREE: QuotaConfig(
        plan=QuotaPlan.FREE,
        daily_limit=FREE_PLAN_DAILY_LIMIT,
        monthly_limit=FREE_PLAN_MONTHLY_LIMIT,
        burst_limit=FREE_PLAN_BURST_LIMIT,
    ),
    QuotaPlan.PRO: QuotaConfig(
        plan=QuotaPlan.PRO,
        daily_limit=PRO_PLAN_DAILY_LIMIT,
        monthly_limit=PRO_PLAN_MONTHLY_LIMIT,
        burst_limit=PRO_PLAN_BURST_LIMIT,
    ),
    QuotaPlan.ENTERPRISE: QuotaConfig(
        plan=QuotaPlan.ENTERPRISE,
        daily_limit=ENTERPRISE_PLAN_DAILY_LIMIT,
        monthly_limit=ENTERPRISE_PLAN_MONTHLY_LIMIT,
        burst_limit=ENTERPRISE_PLAN_BURST_LIMIT,
    ),
    QuotaPlan.UNLIMITED: QuotaConfig(
        plan=QuotaPlan.UNLIMITED,
        daily_limit=float("inf"),
        monthly_limit=float("inf"),
        burst_limit=float("inf"),
    ),
}


class CostQuotaMiddleware:
    """Middleware for enforcing cost-based quotas.

    Tracks actual $ spent on LLM API calls and enforces per-plan limits.
    More accurate than request-based rate limiting for LLM usage.
    """

    def __init__(
        self,
        enabled: bool = True,
        default_plan: QuotaPlan = QuotaPlan.FREE,
    ) -> None:
        """Initialize cost quota middleware.

        Args:
            enabled: Whether cost quota enforcement is enabled
            default_plan: Default plan for users without a plan

        """
        self.enabled = enabled
        self.default_plan = default_plan
        self.hour_window = DEFAULT_QUOTA_HOUR_WINDOW
        self.day_window = DEFAULT_QUOTA_DAY_WINDOW
        self.month_window = DEFAULT_QUOTA_MONTH_WINDOW

        if enabled:
            logger.info(
                f"CostQuotaMiddleware initialized with default plan: {default_plan}"
            )

    async def __call__(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request with cost quota enforcement.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response or quota exceeded error

        """
        if not self._should_enforce_quota(request):
            return await call_next(request)

        quota_key = await self._get_quota_key(request)
        user_plan = await self._get_user_plan(request)

        if not await self._check_quota(quota_key, user_plan):
            logger.warning("Cost quota exceeded for %s (plan: %s)", quota_key, user_plan)
            return await self._quota_exceeded_response(quota_key, user_plan)

        response = await call_next(request)
        await self._annotate_response_with_quota(response, quota_key, user_plan)
        return response

    def _should_enforce_quota(self, request: Request) -> bool:
        if not self.enabled:
            return False

        path = request.url.path
        if path in QUOTA_EXEMPT_PATHS:
            return False
        for prefix in QUOTA_EXEMPT_PATH_PREFIXES:
            if path.startswith(prefix):
                return False
        return True

    async def _annotate_response_with_quota(
        self,
        response: Response,
        quota_key: str,
        plan: QuotaPlan,
    ) -> None:
        remaining = await self._get_remaining_quota(quota_key, plan)
        config = QUOTA_CONFIGS[plan]
        response.headers["X-Cost-Quota-Plan"] = plan.value
        response.headers["X-Cost-Quota-Daily-Limit"] = str(config.daily_limit)
        response.headers["X-Cost-Quota-Daily-Remaining"] = str(remaining["daily"])
        response.headers["X-Cost-Quota-Monthly-Limit"] = str(config.monthly_limit)
        response.headers["X-Cost-Quota-Monthly-Remaining"] = str(remaining["monthly"])

    async def _get_quota_key(self, request: Request) -> str:
        """Get quota key from request.

        Tries to use user_id from auth, falls back to IP address.

        Args:
            request: FastAPI request

        Returns:
            Quota key (user_id or IP)

        """
        # Try to get user_id from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        try:
            import hashlib
            hashed = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:12]
            return "ip:" + hashed
        except Exception:
            return "ip:unknown"

    async def _get_user_plan(self, request: Request) -> QuotaPlan:
        """Get user's quota plan.

        Args:
            request: FastAPI request

        Returns:
            User's quota plan

        """
        # Try to get plan from request state (set by auth middleware)
        plan = getattr(request.state, "quota_plan", None)
        if plan:
            try:
                return QuotaPlan(plan)
            except ValueError:
                pass

        # Fall back to default plan
        return self.default_plan

    async def _check_quota(self, key: str, plan: QuotaPlan) -> bool:
        """Check if user is within cost quota.

        Args:
            key: Quota key
            plan: User's quota plan

        Returns:
            True if within quota, False if exceeded

        """
        current_time = time.time()
        config = QUOTA_CONFIGS[plan]
        cost_data = _cost_store[key]

        self._reset_cost_windows(cost_data, current_time)
        return self._within_limits(cost_data, config)

    def _reset_cost_windows(self, cost_data: dict[str, float], current_time: float) -> None:
        if current_time - cost_data["last_reset_day"] > self.day_window:
            cost_data["daily_cost"] = 0.0
            cost_data["last_reset_day"] = current_time

        if current_time - cost_data["last_reset_month"] > self.month_window:
            cost_data["monthly_cost"] = 0.0
            cost_data["last_reset_month"] = current_time

    def _within_limits(self, cost_data: dict[str, float], config: QuotaConfig) -> bool:
        if cost_data["daily_cost"] >= config.daily_limit:
            logger.debug(
                "Daily quota exceeded: %.2f >= %s",
                cost_data["daily_cost"],
                config.daily_limit,
            )
            return False

        if cost_data["monthly_cost"] >= config.monthly_limit:
            logger.debug(
                "Monthly quota exceeded: %.2f >= %s",
                cost_data["monthly_cost"],
                config.monthly_limit,
            )
            return False
        return True

    async def _get_remaining_quota(self, key: str, plan: QuotaPlan) -> dict[str, float]:
        """Get remaining quota for user.

        Args:
            key: Quota key
            plan: User's quota plan

        Returns:
            Dict with remaining daily and monthly quotas

        """
        config = QUOTA_CONFIGS[plan]
        cost_data = _cost_store[key]

        return {
            "daily": max(0.0, config.daily_limit - cost_data["daily_cost"]),
            "monthly": max(0.0, config.monthly_limit - cost_data["monthly_cost"]),
        }

    async def _quota_exceeded_response(self, key: str, plan: QuotaPlan) -> JSONResponse:
        """Generate quota exceeded response with user-friendly formatting.

        Args:
            key: Quota key
            plan: User's quota plan

        Returns:
            JSONResponse with 429 status and user-friendly error format

        """
        from backend.server.utils.error_formatter import format_quota_exceeded_error
        
        config = QUOTA_CONFIGS[plan]
        cost_data = _cost_store[key]

        # Determine which limit was exceeded
        if cost_data["daily_cost"] >= config.daily_limit:
            limit_type = "daily"
            limit = config.daily_limit
            spent = cost_data["daily_cost"]
            reset_time = int(cost_data["last_reset_day"] + self.day_window)
        else:
            limit_type = "monthly"
            limit = config.monthly_limit
            spent = cost_data["monthly_cost"]
            reset_time = int(cost_data["last_reset_month"] + self.month_window)

        # Format as user-friendly error
        quota_info = {
            "quota_plan": plan.value,
            "limit_type": limit_type,
            "limit": limit,
            "spent": spent,
            "reset_at": reset_time,
        }
        user_error = format_quota_exceeded_error(quota_info)
        payload = user_error.to_dict()
        
        resp = JSONResponse(status_code=429, content=payload)
        resp.headers["Retry-After"] = str(reset_time - int(time.time()))
        resp.headers["X-Cost-Quota-Plan"] = plan.value
        return resp

    def record_cost(self, key: str, cost: float) -> None:
        """Record cost for a user.

        Should be called after LLM API calls to track actual cost.

        Args:
            key: Quota key (user:id or ip:address)
            cost: Cost in dollars

        """
        if not self.enabled:
            return

        cost_data = _cost_store[key]
        cost_data["daily_cost"] += cost
        cost_data["monthly_cost"] += cost

        logger.debug(
            f"Recorded ${cost:.4f} for {key}. "
            f"Daily: ${cost_data['daily_cost']:.2f}, "
            f"Monthly: ${cost_data['monthly_cost']:.2f}"
        )


# Global instance for recording costs from anywhere
_GLOBAL_QUOTA_MIDDLEWARE: CostQuotaMiddleware | None = None


def get_cost_quota_middleware() -> CostQuotaMiddleware:
    """Get or create global cost quota middleware instance.
    
    Auto-detects Redis and uses RedisCostQuotaMiddleware if available,
    otherwise falls back to in-memory CostQuotaMiddleware.
    
    Returns:
        Cost quota middleware instance (Redis-backed if available, otherwise in-memory)
    """
    global _GLOBAL_QUOTA_MIDDLEWARE
    if _GLOBAL_QUOTA_MIDDLEWARE is None:
        # Try Redis first if available
        if REDIS_AVAILABLE:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            try:
                # Create Redis middleware (will be async-initialized on first use)
                _GLOBAL_QUOTA_MIDDLEWARE = RedisCostQuotaMiddleware(
                    redis_url=redis_url,
                    enabled=True,
                    default_plan=QuotaPlan(os.getenv("DEFAULT_QUOTA_PLAN", "free")),
                    connection_pool_size=int(os.getenv("REDIS_POOL_SIZE", "10")),
                    connection_timeout=float(os.getenv("REDIS_TIMEOUT", "5.0")),
                    fallback_enabled=os.getenv("REDIS_QUOTA_FALLBACK", "true").lower() == "true",
                )
                logger.info("Using Redis-backed cost quota middleware")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis quota middleware: {e}. Falling back to in-memory.")
                _GLOBAL_QUOTA_MIDDLEWARE = CostQuotaMiddleware(
                    enabled=True,
                    default_plan=QuotaPlan(os.getenv("DEFAULT_QUOTA_PLAN", "free")),
                )
        else:
            _GLOBAL_QUOTA_MIDDLEWARE = CostQuotaMiddleware(
                enabled=True,
                default_plan=QuotaPlan(os.getenv("DEFAULT_QUOTA_PLAN", "free")),
            )
            logger.info("Using in-memory cost quota middleware (Redis not available)")
    return _GLOBAL_QUOTA_MIDDLEWARE


def record_llm_cost(user_key: str, cost: float) -> None:
    """Record LLM cost for a user.

    Args:
        user_key: User quota key (user:id or ip:address)
        cost: Cost in dollars

    """
    middleware = get_cost_quota_middleware()
    middleware.record_cost(user_key, cost)


# Redis-backed cost quota for production (optional)
try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.info("Redis not available, using in-memory cost tracking")


class RedisCostQuotaMiddleware(CostQuotaMiddleware):
    """Redis-backed cost quota for distributed systems with connection pooling and health checks."""

    def __init__(
        self,
        redis_url: str | None = None,
        enabled: bool = True,
        default_plan: QuotaPlan = QuotaPlan.FREE,
        connection_pool_size: int = 10,
        connection_timeout: float = 5.0,
        fallback_enabled: bool = True,
    ) -> None:
        """Initialize Redis cost quota middleware.

        Args:
            redis_url: Redis connection URL (defaults to REDIS_URL env var)
            enabled: Whether cost quota enforcement is enabled
            default_plan: Default plan for users
            connection_pool_size: Redis connection pool size
            connection_timeout: Redis connection timeout in seconds
            fallback_enabled: Fall back to in-memory if Redis unavailable

        """
        super().__init__(enabled, default_plan)
        # Auto-detect Redis URL from environment if not provided
        env_url = os.getenv("REDIS_URL")
        self.redis_url: str = redis_url or env_url or "redis://localhost:6379"
        self.connection_pool_size = connection_pool_size
        self.connection_timeout = connection_timeout
        self.fallback_enabled = fallback_enabled
        self._redis_client: redis.Redis | None = None
        self._redis_pool: redis.ConnectionPool | None = None
        self._redis_health_check_interval = 60.0  # Health check every 60 seconds
        self._last_health_check = 0.0
        self._redis_healthy = False

        if enabled:
            logger.info(
                f"RedisCostQuotaMiddleware initialized with default plan: {default_plan}, "
                f"redis_url: {self.redis_url}, pool_size: {connection_pool_size}"
            )

    async def _get_redis_client(self) -> redis.Redis | None:
        """Get or create Redis client with connection pooling and health checks.

        Returns:
            Redis client or None if unavailable

        """
        if not self._is_redis_enabled():
            return None

        current_time = time.time()
        await self._health_check_existing_client(current_time)

        if self._redis_client is None:
            await self._establish_new_client(current_time)

        if self._redis_client is None and not self.fallback_enabled:
            logger.error("Redis unavailable and fallback disabled. Quota tracking disabled.")
            return None

        return self._redis_client

    def _is_redis_enabled(self) -> bool:
        if REDIS_AVAILABLE:
            return True
        if self.fallback_enabled:
            logger.debug("Redis not available, using in-memory quota tracking")
        return False

    async def _health_check_existing_client(self, current_time: float) -> None:
        if (
            self._redis_client is None
            or current_time - self._last_health_check <= self._redis_health_check_interval
        ):
            return

        try:
            await self._redis_client.ping()
            self._redis_healthy = True
            self._last_health_check = current_time
        except Exception as exc:
            logger.warning("Redis health check failed: %s. Reconnecting...", exc)
            self._redis_healthy = False
            self._redis_client = None
            self._redis_pool = None

    async def _establish_new_client(self, current_time: float) -> None:
        try:
            self._redis_client = await self._create_redis_client()
            await asyncio.wait_for(
                self._redis_client.ping(), timeout=self.connection_timeout
            )
            self._redis_healthy = True
            self._last_health_check = current_time
            logger.info(
                "Connected to Redis for cost quota tracking (pool_size: %s)",
                self.connection_pool_size,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Redis connection timeout after %ss. %s",
                self.connection_timeout,
                "Falling back to in-memory." if self.fallback_enabled else "Quota tracking disabled.",
            )
            self._redis_client = None
            self._redis_pool = None
            self._redis_healthy = False
        except Exception as exc:
            logger.warning(
                "Failed to connect to Redis: %s. %s",
                exc,
                "Falling back to in-memory." if self.fallback_enabled else "Quota tracking disabled.",
            )
            self._redis_client = None
            self._redis_pool = None
            self._redis_healthy = False

    async def _create_redis_client(self) -> redis.Redis:
        """Create a Redis client using either a connection pool or from_url fallback."""
        connection_pool_cls = getattr(redis, "ConnectionPool", None)
        if connection_pool_cls and hasattr(connection_pool_cls, "from_url"):
            self._redis_pool = connection_pool_cls.from_url(
                self.redis_url,
                max_connections=self.connection_pool_size,
                decode_responses=True,
                socket_connect_timeout=self.connection_timeout,
                socket_timeout=self.connection_timeout,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            return redis.Redis(connection_pool=self._redis_pool)

        from_url = getattr(redis, "from_url", None)
        if from_url:
            return from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=self.connection_timeout,
                socket_timeout=self.connection_timeout,
            )

        raise RuntimeError("Redis module is missing ConnectionPool.from_url and from_url.")

    def _redis_keys(self, key: str) -> RedisQuotaKeys:
        prefix = "cost_quota"
        return RedisQuotaKeys(
            daily=f"{prefix}:daily:{key}",
            monthly=f"{prefix}:monthly:{key}",
            daily_reset=f"{prefix}:daily_reset:{key}",
            monthly_reset=f"{prefix}:monthly_reset:{key}",
        )

    async def _window_cost(
        self,
        redis_client: redis.Redis,
        value_key: str,
        reset_key: str,
        window: float,
        current_time: float,
    ) -> float:
        reset_time = await redis_client.get(reset_key)
        if not self._redis_client_supports_mutation(redis_client):
            return float(await redis_client.get(value_key) or 0.0)

        if reset_time is None or current_time - float(reset_time) > window:
            await redis_client.set(value_key, "0.0")
            await redis_client.set(reset_key, str(current_time))
            await redis_client.expire(value_key, int(window))
            await redis_client.expire(reset_key, int(window))
            return 0.0
        return float(await redis_client.get(value_key) or 0.0)

    @staticmethod
    def _redis_client_supports_mutation(redis_client: redis.Redis) -> bool:
        return all(
            hasattr(redis_client, attr)
            for attr in ("set", "expire")
        )

    def _apply_limit_checks(
        self,
        key: str,
        config: QuotaConfig,
        daily_cost: float,
        monthly_cost: float,
    ) -> bool:
        allowed = True
        if daily_cost >= config.daily_limit:
            allowed = False
            logger.debug(
                "Daily quota exceeded for %s: $%.2f >= $%s",
                key,
                daily_cost,
                config.daily_limit,
            )
        if monthly_cost >= config.monthly_limit:
            allowed = False
            logger.debug(
                "Monthly quota exceeded for %s: $%.2f >= $%s",
                key,
                monthly_cost,
                config.monthly_limit,
            )
        return allowed

    def _should_instrument_redis(self) -> bool:
        enabled_value = os.getenv("OTEL_INSTRUMENT_REDIS")
        if enabled_value is None:
            enabled_value = os.getenv("OTEL_ENABLED", "false")
        if enabled_value.lower() not in ("true", "1", "yes"):
            return False

        sample_str = os.getenv(
            "OTEL_SAMPLE_REDIS",
            os.getenv("OTEL_SAMPLE_DEFAULT", "1.0"),
        )
        try:
            sample_rate = max(0.0, min(1.0, float(sample_str)))
        except Exception:
            sample_rate = 1.0
        return random.random() < sample_rate

    def _record_quota_span(
        self,
        key: str,
        plan: QuotaPlan,
        config: QuotaConfig,
        daily_cost: float,
        monthly_cost: float,
        allowed: bool,
    ) -> None:
        try:
            from opentelemetry import trace as _otel_trace  # type: ignore
            from opentelemetry.trace import SpanKind as _SpanKind  # type: ignore
        except Exception:
            return

        tracer = _otel_trace.get_tracer("forge.redis")
        with tracer.start_as_current_span("quota.check", kind=_SpanKind.CLIENT) as span:
            span.set_attribute("db.system", "redis")
            span.set_attribute("quota.key", key)
            span.set_attribute("quota.plan", plan.value)
            span.set_attribute("quota.daily.cost", float(daily_cost))
            span.set_attribute("quota.monthly.cost", float(monthly_cost))
            span.set_attribute("quota.daily.limit", float(config.daily_limit))
            span.set_attribute("quota.monthly.limit", float(config.monthly_limit))
            span.set_attribute("quota.allowed", bool(allowed))
            ctx = get_trace_context()
            if ctx.get("trace_id"):
                span.set_attribute("forge.trace_id", str(ctx["trace_id"]))

    async def _handle_redis_check_failure(
        self,
        exc: Exception,
        key: str,
        plan: QuotaPlan,
    ) -> bool:
        logger.error(
            "Redis quota check failed: %s. %s",
            exc,
            "Allowing request (fail-open)." if self.fallback_enabled else "Blocking request (fail-closed).",
        )
        if self.fallback_enabled:
            return await super()._check_quota(key, plan)
        return False

    async def _check_quota(self, key: str, plan: QuotaPlan) -> bool:
        """Check quota using Redis.

        Args:
            key: Quota key
            plan: User's plan

        Returns:
            True if within quota, False if exceeded

        """
        redis_client = await self._get_redis_client()

        if redis_client is None:
            return await super()._check_quota(key, plan)

        try:
            current_time = time.time()
            config = QUOTA_CONFIGS[plan]
            redis_keys = self._redis_keys(key)

            daily_cost = await self._window_cost(
                redis_client,
                redis_keys.daily,
                redis_keys.daily_reset,
                self.day_window,
                current_time,
            )
            monthly_cost = await self._window_cost(
                redis_client,
                redis_keys.monthly,
                redis_keys.monthly_reset,
                self.month_window,
                current_time,
            )

            allowed = self._apply_limit_checks(key, config, daily_cost, monthly_cost)

            if self._should_instrument_redis():
                self._record_quota_span(
                    key,
                    plan,
                    config,
                    daily_cost,
                    monthly_cost,
                    allowed,
                )

            return allowed

        except Exception as exc:
            return await self._handle_redis_check_failure(exc, key, plan)

    async def _get_remaining_quota(self, key: str, plan: QuotaPlan) -> dict[str, float]:
        """Get remaining quota for user using Redis.

        Args:
            key: Quota key
            plan: User's plan

        Returns:
            Dict with remaining daily and monthly quotas

        """
        redis_client = await self._get_redis_client()

        # Fall back to in-memory if Redis unavailable
        if redis_client is None:
            return await super()._get_remaining_quota(key, plan)

        try:
            current_time = time.time()
            config = QUOTA_CONFIGS[plan]

            # Get costs from Redis with reset logic
            redis_key_daily = f"cost_quota:daily:{key}"
            redis_key_monthly = f"cost_quota:monthly:{key}"
            redis_key_daily_reset = f"cost_quota:daily_reset:{key}"
            redis_key_monthly_reset = f"cost_quota:monthly_reset:{key}"

            # Get reset timestamps
            daily_reset_time = await redis_client.get(redis_key_daily_reset)
            monthly_reset_time = await redis_client.get(redis_key_monthly_reset)

            # Reset daily counter if needed
            if daily_reset_time is None or current_time - float(daily_reset_time) > self.day_window:
                daily_cost = 0.0
            else:
                daily_cost = float(await redis_client.get(redis_key_daily) or 0.0)

            # Reset monthly counter if needed
            if monthly_reset_time is None or current_time - float(monthly_reset_time) > self.month_window:
                monthly_cost = 0.0
            else:
                monthly_cost = float(await redis_client.get(redis_key_monthly) or 0.0)

            return {
                "daily": max(0.0, config.daily_limit - daily_cost),
                "monthly": max(0.0, config.monthly_limit - monthly_cost),
            }

        except Exception as e:
            logger.error(f"Redis remaining quota check failed: {e}. Falling back to in-memory.")
            # Fall back to in-memory
            return await super()._get_remaining_quota(key, plan)

    def record_cost(self, key: str, cost: float) -> None:
        """Record cost using Redis (async wrapper).

        Args:
            key: Quota key
            cost: Cost in dollars

        """
        if not self.enabled:
            return

        # For sync calls, fall back to in-memory
        # In production, use async context
        super().record_cost(key, cost)

    async def record_cost_async(self, key: str, cost: float) -> None:
        """Record cost using Redis (async version).

        Args:
            key: Quota key
            cost: Cost in dollars

        """
        if not self.enabled:
            return

        redis_client = await self._get_redis_client()
        if redis_client is None:
            super().record_cost(key, cost)
            return

        try:
            current_time = time.time()
            keys = self._redis_keys(key)
            await self._ensure_reset_keys(redis_client, keys, current_time)
            await self._increment_cost_buckets(redis_client, keys, cost)
            self._maybe_instrument_cost_record(key, cost)
        except Exception as exc:
            logger.error("Failed to record cost in Redis: %s", exc)
            if self.fallback_enabled:
                super().record_cost(key, cost)
            else:
                logger.warning(
                    "Redis unavailable and fallback disabled. Cost not recorded for %s",
                    key,
                )

    async def _ensure_reset_keys(
        self,
        redis_client,
        keys: RedisQuotaKeys,
        current_time: float,
    ) -> None:
        if not self._redis_client_supports_mutation(redis_client):
            return

        await self._initialize_reset_key(
            redis_client,
            keys.daily_reset,
            keys.daily,
            self.day_window,
            current_time,
        )
        await self._initialize_reset_key(
            redis_client,
            keys.monthly_reset,
            keys.monthly,
            self.month_window,
            current_time,
        )

    async def _initialize_reset_key(
        self,
        redis_client,
        reset_key: str,
        value_key: str,
        window: float,
        current_time: float,
    ) -> None:
        reset_time = await redis_client.get(reset_key)
        if reset_time is not None:
            return

        await redis_client.set(reset_key, str(current_time))
        if hasattr(redis_client, "expire"):
            await redis_client.expire(reset_key, window)
            await redis_client.set(value_key, "0.0")
            await redis_client.expire(value_key, window)

    async def _increment_cost_buckets(
        self,
        redis_client,
        keys: RedisQuotaKeys,
        cost: float,
    ) -> None:
        await redis_client.incrbyfloat(keys.daily, cost)
        await redis_client.incrbyfloat(keys.monthly, cost)
        if hasattr(redis_client, "expire"):
            await redis_client.expire(keys.daily, self.day_window)
            await redis_client.expire(keys.monthly, self.month_window)

    def _maybe_instrument_cost_record(self, key: str, cost: float) -> None:
        if not self._should_instrument_redis():
            return
        try:
            from opentelemetry import trace as _otel_trace  # type: ignore
            from opentelemetry.trace import SpanKind as _SpanKind  # type: ignore
        except Exception:
            return

        tracer = _otel_trace.get_tracer("forge.redis")
        with tracer.start_as_current_span(
            "quota.record_cost", kind=_SpanKind.CLIENT
        ) as span:
            span.set_attribute("db.system", "redis")
            span.set_attribute("quota.key", key)
            span.set_attribute("quota.cost.usd", float(cost))
            ctx = get_trace_context()
            if ctx.get("trace_id"):
                span.set_attribute("forge.trace_id", str(ctx["trace_id"]))
