"""Server middleware for OpenHands."""

# Import from the middleware.py file (not the directory)
import importlib.util
import sys
from pathlib import Path

from openhands.server.middleware.rate_limiter import (
    REDIS_AVAILABLE,
    EndpointRateLimiter,
    RateLimiter,
    RedisRateLimiter,
)
from openhands.server.middleware.cost_quota import (
    CostQuotaMiddleware,
    RedisCostQuotaMiddleware,
    QuotaPlan,
    record_llm_cost,
)
from openhands.server.middleware.security_headers import (
    CSRFProtection,
    SecurityHeadersMiddleware,
)

server_dir = Path(__file__).parent.parent
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

# Now import from the middleware.py file

middleware_file = server_dir / "middleware.py"
spec = importlib.util.spec_from_file_location("_middleware_file", middleware_file)
if spec and spec.loader:
    _middleware_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_middleware_module)
    CacheControlMiddleware = _middleware_module.CacheControlMiddleware
    InMemoryRateLimiter = _middleware_module.InMemoryRateLimiter
    LocalhostCORSMiddleware = _middleware_module.LocalhostCORSMiddleware
    RateLimitMiddleware = _middleware_module.RateLimitMiddleware
else:
    # Fallback - import directly (might conflict with package name)
    from openhands.server import middleware as _mw

    CacheControlMiddleware = _mw.CacheControlMiddleware
    InMemoryRateLimiter = _mw.InMemoryRateLimiter
    LocalhostCORSMiddleware = _mw.LocalhostCORSMiddleware
    RateLimitMiddleware = _mw.RateLimitMiddleware

__all__ = [
    "CacheControlMiddleware",
    "CostQuotaMiddleware",
    "CSRFProtection",
    "EndpointRateLimiter",
    "InMemoryRateLimiter",
    "LocalhostCORSMiddleware",
    "QuotaPlan",
    "REDIS_AVAILABLE",
    "RateLimitMiddleware",
    "RateLimiter",
    "RedisCostQuotaMiddleware",
    "RedisRateLimiter",
    "SecurityHeadersMiddleware",
    "record_llm_cost",
]
