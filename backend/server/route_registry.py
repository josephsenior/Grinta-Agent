"""Centralised route registration for the Forge FastAPI application.

Call ``register_routes(app)`` from the application factory to attach
all API routers.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from fastapi import FastAPI

from backend.core.logger import forge_logger as logger

if TYPE_CHECKING:
    pass


def register_routes(app: FastAPI) -> None:
    """Mount all API routers on the FastAPI application."""
    from backend.server.routes.conversation import app as conversation_api_router
    from backend.server.routes.features import app as features_router
    from backend.server.routes.feedback import app as feedback_api_router
    from backend.server.routes.files import app as files_api_router
    from backend.server.routes.git import router as git_api_router
    from backend.server.routes.global_export import app as global_export_router
    from backend.server.routes.health import add_health_endpoints
    from backend.server.routes.knowledge_base import router as knowledge_base_router
    from backend.server.routes.manage_conversations import (
        app as manage_conversation_api_router,
    )
    from backend.server.routes.memory import app as memory_router
    from backend.server.routes.monitoring import app as monitoring_router
    from backend.server.routes.public import app as public_api_router
    from backend.server.routes.secrets import router as secrets_router
    from backend.server.routes.settings import app as settings_router
    from backend.server.routes.templates import app as templates_router
    from backend.server.routes.trajectory import app as trajectory_router
    from backend.server.routes.notifications import router as notifications_router
    from backend.server.routes.search import router as search_router
    from backend.server.shared import server_config
    from backend.server.types import AppMode

    app.include_router(public_api_router, tags=["v1", "public"])
    app.include_router(features_router, tags=["v1", "features"])
    app.include_router(files_api_router, tags=["v1", "files"])
    app.include_router(feedback_api_router, tags=["v1", "feedback"])
    app.include_router(conversation_api_router, tags=["v1", "conversations"])
    app.include_router(manage_conversation_api_router, tags=["v1", "conversations"])
    app.include_router(settings_router, tags=["v1", "settings"])
    app.include_router(secrets_router, tags=["v1", "secrets"])
    app.include_router(memory_router, tags=["v1", "memory"])
    app.include_router(monitoring_router, tags=["v1", "monitoring"])
    app.include_router(knowledge_base_router, tags=["v1", "knowledge"])
    app.include_router(templates_router, tags=["v1", "templates"])
    app.include_router(global_export_router, tags=["v1", "export"])
    if server_config.app_mode == AppMode.OSS:
        app.include_router(git_api_router, tags=["v1", "git"])
    app.include_router(trajectory_router, tags=["v1", "trajectory"])
    app.include_router(notifications_router, tags=["v1", "notifications"])
    app.include_router(search_router, tags=["v1", "search"])
    add_health_endpoints(app)

    # Optional: expose a lightweight debug endpoint for sampling configuration
    _sampling_debug_enabled = os.getenv("OTEL_DEBUG_SAMPLING", "false").lower() == "true"
    if _sampling_debug_enabled:
        _register_sampling_debug(app)


def _register_sampling_debug(app: FastAPI) -> None:
    """Register the OTEL sampling debug endpoint."""
    from typing import Optional

    from fastapi import Query
    from fastapi.responses import JSONResponse

    @app.get("/api/monitoring/sampling_debug", tags=["v1", "monitoring"])
    async def sampling_debug(
        path: Optional[str] = Query(
            default=None, description="Optional path to compute effective sample"
        ),
    ):
        # Access sampling config from the app module
        try:
            from backend.server import app as app_module

            route_patterns = getattr(app_module, "_route_sample_patterns", [])
            route_regex = getattr(app_module, "_route_sample_regex", [])
            payload = {
                "otel_enabled": getattr(app_module, "_otel_enabled", False),
                "base_http_sample": getattr(app_module, "_sample_http", 1.0),
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
                effective_rate = getattr(
                    app_module, "get_effective_http_sample", lambda p: 1.0
                )(path)
                payload["effective_for"] = {
                    "path": path,
                    "effective_rate": effective_rate,
                }
            return JSONResponse(payload)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
