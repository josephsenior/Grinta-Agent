"""FastAPI application factory configuring Forge backend routes and middleware."""

import contextlib
import os
import warnings
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi.routing import Mount
from forge.core.logger import forge_logger as logger

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
from fastapi import FastAPI, Request
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
from forge.server.shared import conversation_manager, server_config
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
    async with conversation_manager:
        yield


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
# Order matters: CORS -> versioning -> compression -> security headers -> CSRF -> rate limiting

# 0. CORS (should be first to handle cross-origin requests)
# 🔒 SECURITY: Use LocalhostCORSMiddleware which always allows localhost/127.0.0.1
# while still respecting configured origins for production
from forge.server.middleware import LocalhostCORSMiddleware
app.add_middleware(LocalhostCORSMiddleware)

# 0.5. Request Tracing (add request IDs for debugging)
from forge.server.middleware.request_tracing import RequestTracingMiddleware
app.add_middleware(BaseHTTPMiddleware, dispatch=RequestTracingMiddleware(enabled=True))

# 0.6. API Versioning (after request tracing, before other middleware)
from forge.server.versioning import version_middleware
app.add_middleware(BaseHTTPMiddleware, dispatch=version_middleware)

# 1. Compression (should be first to compress all responses)
app.add_middleware(
    BaseHTTPMiddleware,
    dispatch=CompressionMiddleware(min_compress_size=1024),
)

# 2. Security headers
app.add_middleware(
    BaseHTTPMiddleware,
    dispatch=SecurityHeadersMiddleware(enabled=True),
)

# 3. CSRF protection
# 🔒 SECURITY: Disabled by default to maintain compatibility; enable via env var
csrf_enabled = os.getenv("CSRF_PROTECTION_ENABLED", "false").lower() == "true"
app.add_middleware(
    BaseHTTPMiddleware,
    dispatch=CSRFProtection(enabled=csrf_enabled),
)

# 4. Rate limiting & Cost quotas
# Use Redis-backed rate limiter if REDIS_HOST is configured, otherwise in-memory
rate_limiter_enabled = os.getenv("RATE_LIMITING_ENABLED", "true").lower() == "true"
cost_quota_enabled = os.getenv("COST_QUOTA_ENABLED", "true").lower() == "true"

if REDIS_AVAILABLE and os.getenv("REDIS_HOST"):
    redis_url = f"redis://{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT', '6379')}"
    if redis_password := os.getenv("REDIS_PASSWORD"):
        redis_url = f"redis://:{redis_password}@{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT', '6379')}"

    app.add_middleware(
        BaseHTTPMiddleware,
        dispatch=RedisRateLimiter(
            redis_url=redis_url,
            enabled=rate_limiter_enabled,
        ),
    )
    # Add Redis-backed cost quota middleware
    if cost_quota_enabled:
        logger.info("Using Redis cost quota middleware")
        default_plan = QuotaPlan(os.getenv("DEFAULT_QUOTA_PLAN", "free"))
        app.add_middleware(
            BaseHTTPMiddleware,
            dispatch=RedisCostQuotaMiddleware(
                redis_url=redis_url,
                enabled=True,
                default_plan=default_plan,
            ),
        )
else:
    app.add_middleware(
        BaseHTTPMiddleware,
        dispatch=EndpointRateLimiter(enabled=rate_limiter_enabled),
    )
    # Add in-memory cost quota middleware
    if cost_quota_enabled:
        logger.info("Using in-memory cost quota middleware")
        default_plan = QuotaPlan(os.getenv("DEFAULT_QUOTA_PLAN", "free"))
        app.add_middleware(
            BaseHTTPMiddleware,
            dispatch=CostQuotaMiddleware(
                enabled=True,
                default_plan=default_plan,
            ),
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
    return JSONResponse(
        status_code=401,
        content=user_error.to_dict()
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
async def runtime_unavailable_handler(request: Request, exc: AgentRuntimeUnavailableError):
    """Handle runtime unavailable with user-friendly message."""
    from forge.server.utils.error_formatter import format_error_for_user
    
    error_dict = format_error_for_user(exc, context={"path": request.url.path})
    return JSONResponse(status_code=503, content=error_dict)


@app.exception_handler(FunctionCallValidationError)
async def function_call_error_handler(request: Request, exc: FunctionCallValidationError):
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
add_health_endpoints(app)
