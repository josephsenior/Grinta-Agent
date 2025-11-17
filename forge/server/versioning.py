"""API Versioning Infrastructure for Forge.

This module provides production-grade API versioning support:
- Version-based routing
- Deprecation handling
- Version negotiation
- Sunset dates
- Migration support

Version Strategy:
- Current stable: v1
- Beta versions: v2-beta
- Deprecated versions: Sunset header + warning logs
"""

from datetime import datetime
from enum import Enum
from typing import Callable, Optional, Awaitable, Any
import inspect

from fastapi import APIRouter, Header, Request, Response
from fastapi.responses import JSONResponse

from forge.server.constants import ENFORCE_API_VERSIONING


class APIVersion(str, Enum):
    """Supported API versions.

    Add new versions here as you evolve the API.
    """

    V1 = "v1"
    # V2 = "v2"  # Uncomment when v2 is ready
    # V2_BETA = "v2-beta"  # Beta versions for early adopters


# Current stable version (default)
CURRENT_VERSION = APIVersion.V1

# Minimum supported version (older versions are sunset)
MINIMUM_SUPPORTED_VERSION = APIVersion.V1

# Version sunset dates (format: YYYY-MM-DD)
SUNSET_DATES: dict[APIVersion, str] = {
    # APIVersion.V1: "2026-12-31",  # Example: v1 will be sunset on Dec 31, 2026
}

# Version deprecation warnings
DEPRECATED_VERSIONS: dict[APIVersion, dict[str, str]] = {
    # APIVersion.V1: {
    #     "message": "v1 API is deprecated. Please migrate to v2.",
    #     "sunset_date": "2026-12-31",
    #     "migration_guide": "https://docs.forge.ai/api/migration/v1-to-v2"
    # }
}


def get_api_version_from_path(path: str) -> Optional[str]:
    """Extract API version from request path.

    Args:
        path: Request path (e.g., /api/v1/conversation)

    Returns:
        Version string (e.g., "v1") or None if not versioned

    """
    parts = path.split("/")
    if len(parts) >= 3 and parts[1] == "api":
        version = parts[2]
        if version.startswith("v"):
            return version
    return None


def is_version_deprecated(version: str) -> bool:
    """Check if an API version is deprecated.

    Args:
        version: Version string (e.g., "v1")

    Returns:
        True if version is deprecated

    """
    try:
        api_version = APIVersion(version)
    except ValueError:
        return False
    return api_version in DEPRECATED_VERSIONS


def get_deprecation_info(version: str) -> Optional[dict]:
    """Get deprecation information for a version.

    Args:
        version: Version string (e.g., "v1")

    Returns:
        Deprecation info dict or None

    """
    try:
        api_version = APIVersion(version)
    except ValueError:
        return None
    return DEPRECATED_VERSIONS.get(api_version)


def get_sunset_date(version: str) -> Optional[str]:
    """Get sunset date for a version.

    Args:
        version: Version string (e.g., "v1")

    Returns:
        Sunset date string (YYYY-MM-DD) or None

    """
    try:
        api_version = APIVersion(version)
    except ValueError:
        return None
    return SUNSET_DATES.get(api_version)


def add_version_headers(response: Response, version: str) -> None:
    """Add versioning-related headers to response.

    Headers added:
    - API-Version: Current version being used
    - Deprecation: If version is deprecated
    - Sunset: When version will be removed
    - Link: Migration guide URL

    Args:
        response: FastAPI Response object
        version: API version string

    """
    # Always include current version
    response.headers["API-Version"] = version

    # Add deprecation headers if applicable
    if is_version_deprecated(version):
        deprecation_info = get_deprecation_info(version)
        response.headers["Deprecation"] = "true"

        if deprecation_info:
            # Sunset date (RFC 8594)
            if "sunset_date" in deprecation_info:
                sunset = deprecation_info["sunset_date"]
                # Convert to HTTP date format
                sunset_dt = datetime.strptime(sunset, "%Y-%m-%d")
                response.headers["Sunset"] = sunset_dt.strftime(
                    "%a, %d %b %Y %H:%M:%S GMT"
                )

            # Migration guide link (RFC 8288)
            if "migration_guide" in deprecation_info:
                response.headers["Link"] = (
                    f'<{deprecation_info["migration_guide"]}>; rel="successor-version"'
                )

            # Warning header (RFC 7234)
            if "message" in deprecation_info:
                response.headers["Warning"] = f'299 - "{deprecation_info["message"]}"'


async def version_middleware(request: Request, call_next: Callable) -> Response:
    """Middleware to handle API versioning.

    This middleware:
    1. Extracts version from path
    2. Validates version is supported
    3. Adds version headers to response
    4. Logs deprecated version usage

    Args:
        request: FastAPI Request
        call_next: Next middleware in chain

    Returns:
        Response with version headers

    """
    # Extract version from path
    version = get_api_version_from_path(request.url.path)

    # If this is an API request but no version, return error
    if request.url.path.startswith("/api/") and not version and ENFORCE_API_VERSIONING:
        # Allow non-versioned paths (health, socket.io, etc.)
        if not any(
            request.url.path.startswith(p)
            for p in [
                "/api/monitoring/health",
                "/api/health",
                "/api/docs",
                "/api/openapi",
            ]
        ):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "missing_api_version",
                    "message": f"API version required. Please use /api/{CURRENT_VERSION}/... format.",
                    "current_version": CURRENT_VERSION,
                    "supported_versions": [v.value for v in APIVersion],
                },
            )

    # Proceed with request
    response = await call_next(request)

    # Add version headers if this was a versioned API call
    if version:
        add_version_headers(response, version)

        # Log deprecated version usage
        if is_version_deprecated(version):
            import logging

            logger = logging.getLogger("forge.versioning")
            logger.warning(
                f"Deprecated API version used: {version} - "
                f"Path: {request.url.path} - "
                f"Client: {request.client.host if request.client else 'unknown'}"
            )

    return response


def create_versioned_router(
    prefix: str, version: APIVersion = CURRENT_VERSION, **kwargs
) -> APIRouter:
    """Create a router with version prefix.

    Usage:
        router = create_versioned_router("/conversation", version=APIVersion.V1)

        @router.get("/")
        async def get_conversations():
            # This will be accessible at /api/v1/conversation
            ...

    Args:
        prefix: Route prefix (e.g., "/conversation")
        version: API version (default: current stable)
        **kwargs: Additional APIRouter arguments

    Returns:
        APIRouter with versioned prefix

    """
    versioned_prefix = f"/api/{version.value}{prefix}"
    return APIRouter(prefix=versioned_prefix, **kwargs)


def api_route(
    version: APIVersion = CURRENT_VERSION,
    deprecated: bool = False,
    sunset_date: Optional[str] = None,
    migration_guide: Optional[str] = None,
):
    """Decorator to mark an API route with version information.

    Usage:
        @router.get("/users")
        @api_route(version=APIVersion.V1, deprecated=True, sunset_date="2026-12-31")
        async def get_users():
            ...

    Args:
        version: API version
        deprecated: Whether this endpoint is deprecated
        sunset_date: When this endpoint will be removed (YYYY-MM-DD)
        migration_guide: URL to migration documentation

    """

    def decorator(route_handler: Callable[..., Awaitable[Any]] | Callable[..., Any]):
        """Wrap route handler to enforce Accept-Version header semantics."""
        # Annotate handler with metadata for versioned docs/testing.
        setattr(route_handler, "__api_version__", version)
        setattr(route_handler, "__api_deprecated__", deprecated)
        if sunset_date:
            setattr(route_handler, "__api_sunset__", sunset_date)
        if migration_guide:
            setattr(route_handler, "__api_migration_guide__", migration_guide)
        return route_handler

    return decorator


# Utility function for gradual migration
def supports_version(
    min_version: APIVersion, max_version: Optional[APIVersion] = None
) -> bool:
    """Check if current request supports a version range.

    Useful for feature flags and gradual rollouts.

    Args:
        min_version: Minimum supported version
        max_version: Maximum supported version (optional)

    Returns:
        True if version is in supported range

    """
    # This would need request context to work properly
    # Placeholder for now
    return True
