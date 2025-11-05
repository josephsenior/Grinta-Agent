"""Cost-based quota system for LLM API usage.

Tracks actual $ spent instead of just request counts.
Supports per-user and per-plan quotas (free, pro, enterprise).
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Callable

from fastapi.responses import JSONResponse

from openhands.core.logger import openhands_logger as logger

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


class QuotaPlan(str, Enum):
    """User quota plans."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    UNLIMITED = "unlimited"


@dataclass
class QuotaConfig:
    """Quota configuration for a plan."""

    plan: QuotaPlan
    daily_limit: float  # $ per day
    monthly_limit: float  # $ per month
    burst_limit: float  # $ per hour


# Default quota configs
QUOTA_CONFIGS = {
    QuotaPlan.FREE: QuotaConfig(
        plan=QuotaPlan.FREE,
        daily_limit=1.0,  # $1/day
        monthly_limit=20.0,  # $20/month
        burst_limit=0.5,  # $0.50/hour
    ),
    QuotaPlan.PRO: QuotaConfig(
        plan=QuotaPlan.PRO,
        daily_limit=10.0,  # $10/day
        monthly_limit=200.0,  # $200/month
        burst_limit=5.0,  # $5/hour
    ),
    QuotaPlan.ENTERPRISE: QuotaConfig(
        plan=QuotaPlan.ENTERPRISE,
        daily_limit=100.0,  # $100/day
        monthly_limit=2000.0,  # $2000/month
        burst_limit=50.0,  # $50/hour
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
        self.hour_window = 3600  # 1 hour in seconds
        self.day_window = 86400  # 24 hours
        self.month_window = 2592000  # 30 days

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
        if not self.enabled:
            return await call_next(request)

        # Skip quota checks for health checks and static files
        if request.url.path in ["/health", "/api/health", "/"] or request.url.path.startswith(
            "/assets"
        ):
            return await call_next(request)

        # Get user quota key (user_id or IP)
        quota_key = await self._get_quota_key(request)

        # Get user's plan
        user_plan = await self._get_user_plan(request)

        # Check if user is within quota
        if not await self._check_quota(quota_key, user_plan):
            logger.warning(f"Cost quota exceeded for {quota_key} (plan: {user_plan})")
            return await self._quota_exceeded_response(quota_key, user_plan)

        # Process request
        response = await call_next(request)

        # Add cost quota headers
        remaining = await self._get_remaining_quota(quota_key, user_plan)
        config = QUOTA_CONFIGS[user_plan]

        response.headers["X-Cost-Quota-Plan"] = user_plan.value
        response.headers["X-Cost-Quota-Daily-Limit"] = str(config.daily_limit)
        response.headers["X-Cost-Quota-Daily-Remaining"] = str(remaining["daily"])
        response.headers["X-Cost-Quota-Monthly-Limit"] = str(config.monthly_limit)
        response.headers["X-Cost-Quota-Monthly-Remaining"] = str(remaining["monthly"])

        return response

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

        return f"ip:{client_ip}"

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

        # Get user's cost data
        cost_data = _cost_store[key]

        # Reset daily counter if needed
        if current_time - cost_data["last_reset_day"] > self.day_window:
            cost_data["daily_cost"] = 0.0
            cost_data["last_reset_day"] = current_time

        # Reset monthly counter if needed
        if current_time - cost_data["last_reset_month"] > self.month_window:
            cost_data["monthly_cost"] = 0.0
            cost_data["last_reset_month"] = current_time

        # Check daily limit
        if cost_data["daily_cost"] >= config.daily_limit:
            logger.debug(
                f"Daily quota exceeded: {cost_data['daily_cost']:.2f} >= {config.daily_limit}"
            )
            return False

        # Check monthly limit
        if cost_data["monthly_cost"] >= config.monthly_limit:
            logger.debug(
                f"Monthly quota exceeded: {cost_data['monthly_cost']:.2f} >= {config.monthly_limit}"
            )
            return False

        return True

    async def _get_remaining_quota(
        self, key: str, plan: QuotaPlan
    ) -> dict[str, float]:
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

    async def _quota_exceeded_response(
        self, key: str, plan: QuotaPlan
    ) -> JSONResponse:
        """Generate quota exceeded response.

        Args:
            key: Quota key
            plan: User's quota plan

        Returns:
            JSONResponse with 429 status
        """
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

        return JSONResponse(
            status_code=429,
            content={
                "detail": f"Cost quota exceeded. You've spent ${spent:.2f} of your ${limit} {limit_type} limit.",
                "quota_plan": plan.value,
                "limit_type": limit_type,
                "limit": limit,
                "spent": spent,
                "reset_at": reset_time,
            },
            headers={
                "Retry-After": str(reset_time - int(time.time())),
                "X-Cost-Quota-Plan": plan.value,
            },
        )

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
    """Get or create global cost quota middleware instance."""
    global _GLOBAL_QUOTA_MIDDLEWARE
    if _GLOBAL_QUOTA_MIDDLEWARE is None:
        _GLOBAL_QUOTA_MIDDLEWARE = CostQuotaMiddleware()
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
    logger.debug("Redis not available. Using in-memory cost tracking.")


class RedisCostQuotaMiddleware(CostQuotaMiddleware):
    """Redis-backed cost quota for distributed systems."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        enabled: bool = True,
        default_plan: QuotaPlan = QuotaPlan.FREE,
    ) -> None:
        """Initialize Redis cost quota middleware.

        Args:
            redis_url: Redis connection URL
            enabled: Whether cost quota enforcement is enabled
            default_plan: Default plan for users
        """
        super().__init__(enabled, default_plan)
        self.redis_url = redis_url
        self._redis_client: redis.Redis | None = None

        if enabled:
            logger.info(f"RedisCostQuotaMiddleware initialized with default plan: {default_plan}")

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
                logger.info("Connected to Redis for cost quota tracking")
            except Exception as e:
                logger.warning(
                    f"Failed to connect to Redis: {e}. Falling back to in-memory."
                )
                self._redis_client = None

        return self._redis_client

    async def _check_quota(self, key: str, plan: QuotaPlan) -> bool:
        """Check quota using Redis.

        Args:
            key: Quota key
            plan: User's plan

        Returns:
            True if within quota, False if exceeded
        """
        redis_client = await self._get_redis_client()

        # Fall back to in-memory if Redis unavailable
        if redis_client is None:
            return await super()._check_quota(key, plan)

        try:
            current_time = time.time()
            config = QUOTA_CONFIGS[plan]

            # Get costs from Redis
            redis_key_daily = f"cost_quota:daily:{key}"
            redis_key_monthly = f"cost_quota:monthly:{key}"

            daily_cost = float(await redis_client.get(redis_key_daily) or 0.0)
            monthly_cost = float(await redis_client.get(redis_key_monthly) or 0.0)

            # Check limits
            if daily_cost >= config.daily_limit:
                return False
            if monthly_cost >= config.monthly_limit:
                return False

            return True

        except Exception as e:
            logger.error(f"Redis quota check failed: {e}. Allowing request.")
            # Fail open - allow request if Redis fails
            return True

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
            # Fall back to in-memory
            super().record_cost(key, cost)
            return

        try:
            redis_key_daily = f"cost_quota:daily:{key}"
            redis_key_monthly = f"cost_quota:monthly:{key}"

            # Increment costs
            await redis_client.incrbyfloat(redis_key_daily, cost)
            await redis_client.incrbyfloat(redis_key_monthly, cost)

            # Set expiry (24 hours for daily, 30 days for monthly)
            await redis_client.expire(redis_key_daily, self.day_window)
            await redis_client.expire(redis_key_monthly, self.month_window)

            logger.debug(f"Recorded ${cost:.4f} for {key} in Redis")

        except Exception as e:
            logger.error(f"Failed to record cost in Redis: {e}")
            # Fall back to in-memory
            super().record_cost(key, cost)

