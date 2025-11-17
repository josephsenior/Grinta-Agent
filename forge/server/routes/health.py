"""Health and diagnostics endpoints for the Forge server."""

import sys

from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse

from forge.runtime.utils import system_stats


def get_system_info() -> dict:
    """Proxy to runtime system stats for easier monkeypatching in tests."""
    return system_stats.get_system_info()


def add_health_endpoints(app: FastAPI) -> None:
    """Add health check endpoints to the FastAPI application.

    Args:
        app: The FastAPI application to add endpoints to.

    """

    @app.get("/alive")
    async def alive():
        """Simple liveness probe returning status ok."""
        return {"status": "ok"}

    @app.get("/health")
    async def health(request: Request, response: Response):
        """Deprecated bare health endpoint.

        Returns a deprecation notice pointing to the canonical endpoint.
        """
        accept = (request.headers.get("accept") or "").lower()
        if "text/html" in accept or "application/xhtml+xml" in accept:
            return RedirectResponse(url="/api/monitoring/health", status_code=308)
        # Add deprecation headers for API clients
        response.headers["X-Deprecated-Endpoint"] = "true"
        response.headers["Link"] = '</api/monitoring/health>; rel="successor-version"'
        return {
            "status": "deprecated",
            "use": "/api/monitoring/health",
            "message": "'/health' is deprecated; use '/api/monitoring/health'",
        }

    @app.get("/api/health")
    async def api_health(request: Request, response: Response):
        """Deprecated API health endpoint.

        Returns a deprecation notice pointing to the canonical endpoint.
        """
        accept = (request.headers.get("accept") or "").lower()
        if "text/html" in accept or "application/xhtml+xml" in accept:
            return RedirectResponse(url="/api/monitoring/health", status_code=308)
        # Add deprecation headers for API clients
        response.headers["X-Deprecated-Endpoint"] = "true"
        response.headers["Link"] = '</api/monitoring/health>; rel="successor-version"'
        return {
            "status": "deprecated",
            "use": "/api/monitoring/health",
            "message": "'/api/health' is deprecated; use '/api/monitoring/health'",
        }

    @app.get("/server_info")
    async def get_server_info():
        """Expose system metrics gathered from runtime utilities."""
        module = sys.modules[__name__]
        fetcher = getattr(module, "get_system_info")
        return fetcher()
