"""Server middleware exports.

This package re-exports middleware utilities and classes, including helpers
defined in the sibling module ``forge.server.middleware`` (middleware.py).
We import those helpers via an explicit relative import to avoid recursive
package-import issues and circular initialization.
"""

from __future__ import annotations

import logging
from typing import Any

from forge.server.middleware.rate_limiter import (
    REDIS_AVAILABLE,
    EndpointRateLimiter,
    RateLimiter,
    RedisRateLimiter,
)
from forge.server.middleware.cost_quota import (
    CostQuotaMiddleware,
    RedisCostQuotaMiddleware,
    QuotaPlan,
    record_llm_cost,
)
from forge.server.middleware.security_headers import (
    CSRFProtection,
    SecurityHeadersMiddleware,
)
from forge.server.middleware.request_metrics import RequestMetricsMiddleware
from forge.server.middleware.request_size import RequestSizeLoggingMiddleware

# Import helpers from the sibling module middleware.py deterministically to
# avoid importing the package name "forge.server.middleware" recursively.
from ..middleware_core import (
    CacheControlMiddleware,
    InMemoryRateLimiter,
    LocalhostCORSMiddleware,
    RateLimitMiddleware,
)
logger = logging.getLogger("forge.middleware")

__all__ = [
    "CacheControlMiddleware",
    "CostQuotaMiddleware",
    "CSRFProtection",
    "EndpointRateLimiter",
    "InMemoryRateLimiter",
    "LocalhostCORSMiddleware",
    "QuotaPlan",
    "RequestMetricsMiddleware",
    "RequestSizeLoggingMiddleware",
    "REDIS_AVAILABLE",
    "RateLimitMiddleware",
    "RateLimiter",
    "RedisCostQuotaMiddleware",
    "RedisRateLimiter",
    "SecurityHeadersMiddleware",
    "record_llm_cost",
]
