"""FastAPI application factory configuring Forge backend routes and middleware."""

import contextlib
import os
import warnings
from collections.abc import AsyncIterator
import re
from contextlib import asynccontextmanager
import sys

from fastapi.routing import Mount
from forge.core.logger import forge_logger as logger, get_trace_context
from forge.core.tracing import initialize_tracing

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from forge import __version__
from forge.integrations.service_types import AuthenticationError
from forge.core.exceptions import (
    AgentStuckInLoopError,
    LLMContextWindowExceedError,
    LLMNoResponseError,
    AgentRuntimeUnavailableError,
    FunctionCallValidationError,
    LLMMalformedActionError,
)
from forge.server.middleware.compression import CompressionMiddleware
from forge.server.middleware.rate_limiter import (
    REDIS_AVAILABLE,
    EndpointRateLimiter,
    RedisRateLimiter,
)
from forge.server.middleware.cost_quota import (
    CostQuotaMiddleware,
    RedisCostQuotaMiddleware,
    QuotaPlan,
)
from forge.server.middleware.observability import RequestObservabilityMiddleware
from forge.server.middleware.security_headers import (
    CSRFProtection,
    SecurityHeadersMiddleware,
)
from forge.server.routes.analytics import app as analytics_router
from forge.server.routes.conversation import app as conversation_api_router
from forge.server.routes.database_connections import (
    app as database_connections_router,
)
from forge.server.routes.feedback import app as feedback_api_router
from forge.server.routes.files import app as files_api_router
from forge.server.routes.git import router as git_api_router
from forge.server.routes.global_export import app as global_export_router
from forge.server.routes.health import add_health_endpoints
from forge.server.routes.knowledge_base import router as knowledge_base_router
from forge.server.routes.manage_conversations import (
    app as manage_conversation_api_router,
)

# Delay MCP import to avoid circular dependency issues during config loading
# from forge.server.routes.mcp import mcp_server
from forge.server.routes.memory import app as memory_router
from forge.server.routes.metasop import app as metasop_router
from forge.server.routes.monitoring import app as monitoring_router
from forge.server.routes.prompts import app as prompts_router
from forge.server.routes.prompt_optimization import router as prompt_optimization_router
from forge.server.routes.public import app as public_api_router
from forge.server.routes.secrets import router as secrets_router
from forge.server.routes.security import app as security_api_router
from forge.server.routes.settings import app as settings_router
from forge.server.routes.slack import router as slack_router
from forge.server.routes.snippets import router as snippets_router
from forge.server.routes.templates import app as templates_router
from forge.server.routes.trajectory import app as trajectory_router
from forge.server.routes.dashboard import router as dashboard_router
from forge.server.routes.profile import router as profile_router
from forge.server.routes.notifications import router as notifications_router
from forge.server.routes.search import router as search_router
from forge.server.routes.activity import router as activity_router
from forge.server.shared import conversation_manager, server_config, get_conversation_manager
from forge.server.types import AppMode

# Import MCP server late to ensure config is loaded first
from forge.server.routes.mcp import mcp_server

mcp_app = mcp_server.http_app(path="/mcp")


def combine_lifespans(*lifespans):
    """Combine multiple FastAPI lifespan functions into a single lifespan.

    Args:
        *lifespans: Variable number of lifespan functions to combine.

    Returns:
        Combined lifespan function that runs all provided lifespans.

    """

    @contextlib.asynccontextmanager
    async def combined_lifespan(app):
        """Execute each provided lifespan sequentially within a single ExitStack."""
        async with contextlib.AsyncExitStack() as stack:
            for lifespan in lifespans:
                await stack.enter_async_context(lifespan(app))
            yield

    return combined_lifespan


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application-specific resources during startup/shutdown."""
    # Startup
    logger.info("Starting Forge server...")
    
    # Initialize Sentry error tracking (if configured)
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
            
            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
                release=os.getenv("SENTRY_RELEASE", __version__),
                traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
                sample_rate=float(os.getenv("SENTRY_SAMPLE_RATE", "1.0")),
                integrations=[
                    FastApiIntegration(),
                    SqlalchemyIntegration(),
                ],
            )
            logger.info("Sentry error tracking initialized")
        except ImportError:
            logger.warning("sentry-sdk not installed. Install with: pip install sentry-sdk")
        except Exception as e:
            logger.warning(f"Sentry initialization failed: {e}")
    
    # Register shutdown handlers for graceful shutdown
    from forge.server.graceful_shutdown import register_shutdown_handler

    async def cleanup_conversations():
        """Cleanup all active conversations on shutdown."""
        try:
            manager = await get_conversation_manager().__aenter__()
            # Get all running conversations and stop them gracefully
            running_sids = await manager.get_running_agent_loops()
            logger.info(f"Stopping {len(running_sids)} active conversations...")
            for sid in running_sids:
                try:
                    # Stop conversation gracefully
                    await manager.close_session(sid)
                except Exception as e:
                    logger.error(f"Error stopping conversation {sid}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error during conversation cleanup: {e}", exc_info=True)

    async def cleanup_socketio():
        """Close Socket.IO connections gracefully."""
        try:
            from forge.server.shared import sio
            logger.info("Closing Socket.IO connections...")
            await sio.disconnect()
        except Exception as e:
            logger.error(f"Error closing Socket.IO: {e}", exc_info=True)

    register_shutdown_handler(cleanup_conversations)
    register_shutdown_handler(cleanup_socketio)

    # Lazily initialize the conversation manager to avoid None during import time
    async with get_conversation_manager():
        logger.info("Forge server started successfully")
        yield
        # Shutdown
        logger.info("Shutting down Forge server...")
        from forge.server.graceful_shutdown import graceful_shutdown

        await graceful_shutdown()


app = FastAPI(
    title="Forge API",
    description=(
        "Forge: Production-grade AI development platform\n\n"
        "Features:\n"
        "- Multi-agent orchestration (MetaSOP)\n"
        "- Structure-aware code editing\n"
        "- Real-time collaboration\n"
        "- Enterprise security & monitoring\n\n"
        "Documentation: https://docs.forge.ai\n"
        "Support: support@forge.ai"
    ),
    version=__version__,
    lifespan=combine_lifespans(_lifespan, mcp_app.lifespan),
    routes=[Mount(path="/mcp", app=mcp_app)],
    # OpenAPI configuration
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc alternative
    openapi_url="/openapi.json",  # OpenAPI spec
    openapi_tags=[
        {"name": "v1", "description": "Stable API - Version 1 (current)"},
        {"name": "conversations", "description": "Conversation management endpoints"},
        {"name": "files", "description": "File operations and workspace management"},
        {"name": "settings", "description": "User settings and configuration"},
        {"name": "monitoring", "description": "Metrics and system health"},
        {"name": "metasop", "description": "Multi-agent orchestration"},
    ],
)

# Add security and performance middleware
# Order matters: CORS -> auth -> versioning -> compression -> security headers -> CSRF -> rate limiting -> resource quotas

# 0. CORS (should be first to handle cross-origin requests)
# 🔒 SECURITY: Use LocalhostCORSMiddleware which always allows localhost/127.0.0.1
# while still respecting configured origins for production
from forge.server.middleware import LocalhostCORSMiddleware

app.add_middleware(LocalhostCORSMiddleware)

# 0.25. Authentication (after CORS, before other middleware)
# Optional: Enable JWT authentication if AUTH_ENABLED is set
auth_enabled = os.getenv("AUTH_ENABLED", "false").lower() in ("true", "1", "yes")
if auth_enabled:
    from forge.server.middleware.auth import AuthMiddleware

    app.add_middleware(AuthMiddleware)
    logger.info("JWT authentication middleware enabled")

# 0.5. Request ID (add unique request IDs for tracing)
from forge.server.middleware.request_id import RequestIDMiddleware

app.add_middleware(RequestIDMiddleware)

# 0.6. Request Tracing (add request IDs for debugging)
from forge.server.middleware.request_tracing import RequestTracingMiddleware

app.add_middleware(BaseHTTPMiddleware, dispatch=RequestTracingMiddleware(enabled=True))

# Initialize distributed tracing (defaults to enabled with console exporter)
_tracing_enabled = os.getenv("TRACING_ENABLED", os.getenv("OTEL_ENABLED", "true")).lower() in (
    "true",
    "1",
    "yes",
)
if _tracing_enabled:
    try:
        _tracing_sample_rate = float(
            os.getenv("TRACING_SAMPLE_RATE", os.getenv("OTEL_SAMPLE_DEFAULT", "0.1"))
        )
    except Exception:
        _tracing_sample_rate = 0.1
    initialize_tracing(
        service_name=os.getenv("TRACING_SERVICE_NAME", os.getenv("SERVICE_NAME", "forge-server")),
        service_version=os.getenv("TRACING_SERVICE_VERSION", __version__),
        exporter=os.getenv("TRACING_EXPORTER", os.getenv("OTEL_EXPORTER", "console")),
        endpoint=os.getenv("TRACING_ENDPOINT", os.getenv("OTEL_EXPORTER_ENDPOINT")),
        sample_rate=_tracing_sample_rate,
        enabled=True,
    )

# Minimal OpenTelemetry spans around request lifecycle (optional)
_otel_enabled = _tracing_enabled
try:
    _sample_http = float(
        os.getenv("OTEL_SAMPLE_HTTP", os.getenv("OTEL_SAMPLE_DEFAULT", "0.1"))
    )
except Exception:
    _sample_http = 1.0
_sample_http = max(0.0, min(1.0, _sample_http))
_route_override_raw = os.getenv("OTEL_SAMPLE_ROUTES", "").strip()
_route_sample_patterns = []  # list of tuples (pattern, rate, is_prefix)
if _route_override_raw:
    for item in _route_override_raw.split(";"):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            continue
        pattern, rate_str = item.split(":", 1)
        pattern = pattern.strip()
        try:
            rate = float(rate_str.strip())
        except Exception:
            rate = 1.0
        rate = max(0.0, min(1.0, rate))
        is_prefix = pattern.endswith("*")
        if is_prefix:
            pattern = pattern[:-1]  # remove trailing * for matching
        # Ignore invalid/empty patterns or ones not starting with '/'
        if not pattern or not pattern.startswith("/"):
            continue
        _route_sample_patterns.append((pattern, rate, is_prefix))

_route_regex_raw = os.getenv("OTEL_SAMPLE_ROUTES_REGEX", "").strip()
_route_sample_regex = []  # list of tuples (compiled_regex, rate)
if _route_regex_raw:
    for item in _route_regex_raw.split(";"):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            continue
        pattern, rate_str = item.split(":", 1)
        pattern = pattern.strip()
        try:
            rate = float(rate_str.strip())
        except Exception:
            rate = 1.0
        rate = max(0.0, min(1.0, rate))
        if not pattern:
            continue
        try:
            compiled = re.compile(pattern)
        except Exception:
            continue
        _route_sample_regex.append((compiled, rate))


def get_effective_http_sample(route_path: str) -> float:
    """Return effective sampling probability for a given HTTP route.

    Order of precedence:
    1. First matching entry in `_route_sample_regex` (left-to-right regex matches) — fine-grained override.
    2. First matching entry in `_route_sample_patterns` (exact or prefix `*`).
    3. Fallback to base `_sample_http` from `OTEL_SAMPLE_HTTP` or `OTEL_SAMPLE_DEFAULT`.

    Args:
        route_path: The HTTP route path (e.g. "/api/conversations/123").

    Returns:
        Sampling probability in [0.0, 1.0].
    """
    try:
        # Regex overrides take precedence
        for cregex, rate in _route_sample_regex:
            if cregex.search(route_path):
                return rate
        # Then exact/prefix patterns
        for pattern, rate, is_prefix in _route_sample_patterns:
            if (is_prefix and route_path.startswith(pattern)) or (
                not is_prefix and route_path == pattern
            ):
                return rate
    except Exception:
        pass
    return _sample_http


if _otel_enabled:
    try:  # pragma: no cover - optional instrumentation
        from opentelemetry import trace
        from opentelemetry.trace import SpanKind

        tracer = trace.get_tracer("forge.server")

        async def otel_wrapper(request: Request, call_next):
            route_path = getattr(
                getattr(request.scope.get("route", None), "path", None),
                "__str__",
                lambda: None,
            )()
            if not route_path:
                route_path = request.url.path
            # Determine effective sample rate using helper (regex > simple > base)
            effective_rate = get_effective_http_sample(route_path)
            # Head sampling: skip span creation if random() > effective_rate
            import random

            if random.random() > effective_rate:
                return await call_next(request)
            with tracer.start_as_current_span(
                name=f"HTTP {request.method} {route_path}", kind=SpanKind.SERVER
            ) as span:
                span.set_attribute("http.method", request.method)
                span.set_attribute("http.route", route_path)
                span.set_attribute("http.target", request.url.path)
                span.set_attribute("http.url", str(request.url))
                span.set_attribute(
                    "forge.request_id",
                    getattr(getattr(request, "state", object()), "request_id", ""),
                )
                # Bridge thread-local orchestrator trace_id for correlation
                try:
                    ctx = get_trace_context()
                    tid = ctx.get("trace_id") if isinstance(ctx, dict) else None
                    if tid:
                        span.set_attribute("forge.trace_id", str(tid))
                except Exception:
                    pass
                try:
                    response = await call_next(request)
                    span.set_attribute("http.status_code", response.status_code)
                except Exception as e:
                    span.record_exception(e)
                    span.set_attribute("error", True)
                    raise
                return response

        app.add_middleware(BaseHTTPMiddleware, dispatch=otel_wrapper)
    except Exception as e:  # pragma: no cover
        logger.warning(f"OTEL instrumentation initialization failed: {e}")

# 0.6. API Versioning (after request tracing, before other middleware)
from forge.server.versioning import version_middleware

app.add_middleware(BaseHTTPMiddleware, dispatch=version_middleware)

# 0.65. Request Metrics (lightweight Prometheus-friendly counters/histogram)
from forge.server.middleware import RequestMetricsMiddleware

app.add_middleware(BaseHTTPMiddleware, dispatch=RequestMetricsMiddleware(enabled=True))
from forge.server.middleware import RequestSizeLoggingMiddleware

app.add_middleware(
    BaseHTTPMiddleware, dispatch=RequestSizeLoggingMiddleware(enabled=True)
)

# 1. Compression (should be first to compress all responses)
app.add_middleware(
    BaseHTTPMiddleware,
    dispatch=CompressionMiddleware(min_compress_size=1024),
)

# 2. Security headers
# CSP policy can be toggled via env: CSP_POLICY=permissive|strict
# Default: strict in production-like environments, permissive otherwise
env_hint = (
    os.getenv("FORGE_ENV")
    or os.getenv("ENV")
    or os.getenv("PYTHON_ENV")
    or os.getenv("NODE_ENV")
    or "development"
).lower()
default_csp = (
    "strict" if any(x in env_hint for x in ("prod", "production")) else "permissive"
)
csp_policy = os.getenv("CSP_POLICY", default_csp).lower()
if csp_policy not in ("permissive", "strict"):
    csp_policy = default_csp
app.add_middleware(
    BaseHTTPMiddleware,
    dispatch=SecurityHeadersMiddleware(enabled=True, csp_profile=csp_policy),
)

# 3. CSRF protection
# 🔒 SECURITY: Default enabled in production-like environments; can be overridden
default_csrf = "true" if any(x in env_hint for x in ("prod", "production")) else "false"
csrf_enabled = os.getenv("CSRF_PROTECTION_ENABLED", default_csrf).lower() == "true"
app.add_middleware(
    BaseHTTPMiddleware,
    dispatch=CSRFProtection(enabled=csrf_enabled),
)

# 4. Resource Quotas (before rate limiting to check quotas first)
resource_quota_enabled = os.getenv("RESOURCE_QUOTA_ENABLED", "true").lower() == "true"
if resource_quota_enabled:
    from forge.server.middleware.resource_quota import ResourceQuotaMiddleware

    app.add_middleware(ResourceQuotaMiddleware, enabled=True)
    logger.info("Resource quota middleware enabled")

# 4.5. Rate limiting & Cost quotas
# Use Redis-backed rate limiter if REDIS_URL or REDIS_HOST is configured, otherwise in-memory
rate_limiter_enabled = os.getenv("RATE_LIMITING_ENABLED", "true").lower() == "true"
cost_quota_enabled = os.getenv("COST_QUOTA_ENABLED", "true").lower() == "true"

# Auto-detect Redis URL from environment (REDIS_URL takes precedence over REDIS_HOST)
redis_url = os.getenv("REDIS_URL")
if not redis_url and os.getenv("REDIS_HOST"):
    redis_url = f"redis://{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT', '6379')}"
    if redis_password := os.getenv("REDIS_PASSWORD"):
        redis_url = f"redis://:{redis_password}@{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT', '6379')}"

# 0.26. Auth Rate Limiting (after auth, before general rate limiting)
# Stricter rate limiting for auth endpoints to prevent brute force attacks
auth_rate_limiting_enabled = os.getenv("AUTH_RATE_LIMITING_ENABLED", "true").lower() in ("true", "1", "yes")
if auth_rate_limiting_enabled:
    from forge.server.middleware.auth_rate_limiter import (
        AuthRateLimiter,
        RedisAuthRateLimiter,
    )

    # Use Redis if available, otherwise in-memory
    if REDIS_AVAILABLE and redis_url:
        app.add_middleware(
            BaseHTTPMiddleware,
            dispatch=RedisAuthRateLimiter(
                redis_url=redis_url,
                enabled=True,
                login_attempts_per_15min=int(os.getenv("AUTH_LOGIN_ATTEMPTS_PER_15MIN", "5")),
                register_attempts_per_hour=int(os.getenv("AUTH_REGISTER_ATTEMPTS_PER_HOUR", "3")),
                password_reset_per_hour=int(os.getenv("AUTH_PASSWORD_RESET_PER_HOUR", "3")),
            ),
        )
        logger.info("Using Redis-backed auth rate limiter")
    else:
        app.add_middleware(
            BaseHTTPMiddleware,
            dispatch=AuthRateLimiter(
                enabled=True,
                login_attempts_per_15min=int(os.getenv("AUTH_LOGIN_ATTEMPTS_PER_15MIN", "5")),
                register_attempts_per_hour=int(os.getenv("AUTH_REGISTER_ATTEMPTS_PER_HOUR", "3")),
                password_reset_per_hour=int(os.getenv("AUTH_PASSWORD_RESET_PER_HOUR", "3")),
            ),
        )
        logger.info("Using in-memory auth rate limiter (Redis not available)")

# Use Redis if available, otherwise fall back to in-memory
if REDIS_AVAILABLE and redis_url:
    app.add_middleware(
        BaseHTTPMiddleware,
        dispatch=RedisRateLimiter(
            redis_url=redis_url,
            enabled=rate_limiter_enabled,
        ),
    )
    # Add Redis-backed cost quota middleware with connection pooling and health checks
    if cost_quota_enabled:
        logger.info("Using Redis cost quota middleware with connection pooling")
        default_plan = QuotaPlan(os.getenv("DEFAULT_QUOTA_PLAN", "free"))
        connection_pool_size = int(os.getenv("REDIS_POOL_SIZE", "10"))
        connection_timeout = float(os.getenv("REDIS_TIMEOUT", "5.0"))
        fallback_enabled = os.getenv("REDIS_QUOTA_FALLBACK", "true").lower() == "true"
        app.add_middleware(
            BaseHTTPMiddleware,
            dispatch=RedisCostQuotaMiddleware(
                redis_url=redis_url,
                enabled=True,
                default_plan=default_plan,
                connection_pool_size=connection_pool_size,
                connection_timeout=connection_timeout,
                fallback_enabled=fallback_enabled,
            ),
        )
else:
    app.add_middleware(
        BaseHTTPMiddleware,
        dispatch=EndpointRateLimiter(enabled=rate_limiter_enabled),
    )
    # Add in-memory cost quota middleware with graceful fallback message
    if cost_quota_enabled:
        logger.info(
            "Using in-memory cost quota middleware (Redis not available). "
            "Set REDIS_URL to enable distributed quota tracking."
        )
        default_plan = QuotaPlan(os.getenv("DEFAULT_QUOTA_PLAN", "free"))
        app.add_middleware(
            BaseHTTPMiddleware,
            dispatch=CostQuotaMiddleware(
                enabled=True,
                default_plan=default_plan,
            ),
        )

# 5. Observability middleware (requests metrics, SLO tracking, and alerting)
observability_enabled = os.getenv("OBSERVABILITY_ENABLED", "true").lower() in ("true", "1", "yes")
alerting_enabled = os.getenv("ALERTING_ENABLED", "false").lower() in ("true", "1", "yes")
if observability_enabled:
    app.add_middleware(
        RequestObservabilityMiddleware,
        alerting_enabled=alerting_enabled,
    )


@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors by returning 401 status with user-friendly message.

    Args:
        request: The HTTP request that caused the authentication error.
        exc: The authentication exception.

    Returns:
        JSONResponse: 401 status with user-friendly error message.

    """
    from forge.server.utils.error_formatter import format_authentication_error

    user_error = format_authentication_error(exc, context={"path": request.url.path})
    return JSONResponse(status_code=401, content=user_error.to_dict())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with user-friendly messages.
    
    Args:
        request: The HTTP request that caused the validation error.
        exc: The validation exception.
        
    Returns:
        JSONResponse: 400 status with validation error details.
    """
    # Log the raw request body for debugging
    try:
        body = await request.body()
        logger.error(f"Validation error for {request.url.path}: {exc.errors()}")
        logger.error(f"Request body: {body.decode('utf-8') if body else 'empty'}")
    except Exception as e:
        logger.error(f"Could not read request body: {e}")
    
    # Format validation errors for user
    error_messages = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Validation error")
        error_type = err.get("type", "unknown")
        error_messages.append(f"{field}: {msg} (type: {error_type})")
    
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation Error",
            "message": "Invalid request parameters",
            "details": error_messages,
            "path": request.url.path,
        }
    )


# Additional exception handlers for common errors
@app.exception_handler(LLMNoResponseError)
async def llm_no_response_handler(request: Request, exc: LLMNoResponseError):
    """Handle LLM no response errors with user-friendly message."""
    from forge.server.utils.error_formatter import format_error_for_user

    error_dict = format_error_for_user(exc, context={"path": request.url.path})
    return JSONResponse(status_code=503, content=error_dict)


@app.exception_handler(LLMContextWindowExceedError)
async def context_window_handler(request: Request, exc: LLMContextWindowExceedError):
    """Handle context window exceeded with user-friendly message."""
    from forge.server.utils.error_formatter import format_error_for_user

    error_dict = format_error_for_user(exc, context={"path": request.url.path})
    return JSONResponse(status_code=400, content=error_dict)


@app.exception_handler(AgentStuckInLoopError)
async def agent_stuck_handler(request: Request, exc: AgentStuckInLoopError):
    """Handle agent stuck in loop with user-friendly message."""
    from forge.server.utils.error_formatter import format_error_for_user

    error_dict = format_error_for_user(exc, context={"path": request.url.path})
    return JSONResponse(status_code=409, content=error_dict)


@app.exception_handler(AgentRuntimeUnavailableError)
async def runtime_unavailable_handler(
    request: Request, exc: AgentRuntimeUnavailableError
):
    """Handle runtime unavailable with user-friendly message."""
    from forge.server.utils.error_formatter import format_error_for_user

    error_dict = format_error_for_user(exc, context={"path": request.url.path})
    return JSONResponse(status_code=503, content=error_dict)


@app.exception_handler(FunctionCallValidationError)
async def function_call_error_handler(
    request: Request, exc: FunctionCallValidationError
):
    """Handle function call errors with user-friendly message."""
    from forge.server.utils.error_formatter import format_error_for_user

    error_dict = format_error_for_user(exc, context={"path": request.url.path})
    return JSONResponse(status_code=422, content=error_dict)


@app.exception_handler(LLMMalformedActionError)
async def malformed_action_handler(request: Request, exc: LLMMalformedActionError):
    """Handle malformed action errors with user-friendly message."""
    from forge.server.utils.error_formatter import format_error_for_user

    error_dict = format_error_for_user(exc, context={"path": request.url.path})
    return JSONResponse(status_code=422, content=error_dict)


# Generic exception handler (catch-all for any unhandled errors)
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions with user-friendly messages.

    This is the safety net - formats any error gracefully for users.
    """
    from forge.server.utils.error_formatter import safe_format_error

    # Log the raw error for debugging
    logger.exception(f"Unhandled exception: {type(exc).__name__}")

    # Format for users
    error_dict = safe_format_error(exc, context={"path": request.url.path})
    return JSONResponse(status_code=500, content=error_dict)


# Include all routers with v1 versioning tags
# Note: Routes keep their current paths for backward compatibility during beta
# Version headers are added via middleware
# Authentication routes (before other routes for proper middleware order)
from forge.server.routes.auth import router as auth_router

app.include_router(auth_router, tags=["v1", "authentication"])

# User management routes
from forge.server.routes.user_management import router as user_management_router

app.include_router(user_management_router, tags=["v1", "user-management"])

app.include_router(public_api_router, tags=["v1", "public"])
app.include_router(files_api_router, tags=["v1", "files"])
app.include_router(security_api_router, tags=["v1", "security"])
app.include_router(feedback_api_router, tags=["v1", "feedback"])
app.include_router(conversation_api_router, tags=["v1", "conversations"])
app.include_router(manage_conversation_api_router, tags=["v1", "conversations"])
app.include_router(settings_router, tags=["v1", "settings"])
app.include_router(secrets_router, tags=["v1", "secrets"])
app.include_router(database_connections_router, tags=["v1", "database"])
app.include_router(memory_router, tags=["v1", "memory"])
app.include_router(metasop_router, tags=["v1", "metasop"])
app.include_router(monitoring_router, tags=["v1", "monitoring"])
app.include_router(knowledge_base_router, tags=["v1", "knowledge"])
app.include_router(analytics_router, tags=["v1", "analytics"])
app.include_router(prompts_router, tags=["v1", "prompts"])
app.include_router(prompt_optimization_router, tags=["v1", "optimization"])
app.include_router(snippets_router, tags=["v1", "snippets"])
app.include_router(templates_router, tags=["v1", "templates"])
app.include_router(global_export_router, tags=["v1", "export"])
app.include_router(slack_router, prefix="/api/slack", tags=["v1", "integrations"])
if server_config.app_mode == AppMode.OSS:
    app.include_router(git_api_router, tags=["v1", "git"])
app.include_router(trajectory_router, tags=["v1", "trajectory"])
# Billing routes (only enabled when ENABLE_BILLING is true)
from forge.server.routes.billing import router as billing_router

app.include_router(billing_router, tags=["v1", "billing"])
app.include_router(dashboard_router, tags=["v1", "dashboard"])
app.include_router(profile_router, tags=["v1", "profile"])
app.include_router(notifications_router, tags=["v1", "notifications"])
app.include_router(search_router, tags=["v1", "search"])
app.include_router(activity_router, tags=["v1", "activity"])
add_health_endpoints(app)

# Optional: expose a lightweight debug endpoint for sampling configuration
_sampling_debug_enabled = os.getenv("OTEL_DEBUG_SAMPLING", "false").lower() == "true"
if _sampling_debug_enabled:
    from typing import Optional
    from fastapi import Query

    @app.get(
        "/api/monitoring/sampling_debug", tags=["v1", "monitoring"]
    )  # pragma: no cover - covered via integration test
    async def sampling_debug(
        path: Optional[str] = Query(
            default=None, description="Optional path to compute effective sample"
        ),
    ):
        module = sys.modules[__name__]
        try:
            route_patterns = getattr(module, "_route_sample_patterns")
            route_regex = getattr(module, "_route_sample_regex")
            payload = {
                "otel_enabled": getattr(module, "_otel_enabled"),
                "base_http_sample": getattr(module, "_sample_http"),
                "route_patterns": [
                    {
                        "pattern": pattern,
                        "rate": rate,
                        "type": ("prefix" if is_prefix else "exact"),
                    }
                    for pattern, rate, is_prefix in route_patterns
                ],
                "regex_patterns": [
                    {"pattern": cregex.pattern, "rate": rate}
                    for cregex, rate in route_regex
                ],
            }
            if path:
                effective_rate = getattr(module, "get_effective_http_sample")(path)
                payload["effective_for"] = {
                    "path": path,
                    "effective_rate": effective_rate,
                }
            return JSONResponse(payload)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
