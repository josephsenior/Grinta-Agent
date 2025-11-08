"""Socket.IO entrypoint that mounts the FastAPI app and static frontend."""

import os

import socketio  # type: ignore[import-untyped]
from fastapi import Request
from fastapi.staticfiles import StaticFiles

from forge.core.logger import forge_logger as logger
from forge.server.app import app as base_app
from forge.server.middleware import (
    CacheControlMiddleware,
    InMemoryRateLimiter,
    LocalhostCORSMiddleware,
    RateLimitMiddleware,
)
from forge.server.shared import sio
from forge.server.static import SPAStaticFiles

# Import Socket.IO handlers to register them - this MUST be after sio is imported
try:
    import forge.server.listen_socket  # noqa: F401
    logger.debug("Socket.IO handlers registered successfully")
except Exception as e:
    logger.error(f"Failed to import Socket.IO handlers: {e}", exc_info=True)


# Add middleware to base_app first
base_app.add_middleware(LocalhostCORSMiddleware)
base_app.add_middleware(CacheControlMiddleware)
base_app.add_middleware(RateLimitMiddleware, rate_limiter=InMemoryRateLimiter(requests=10, seconds=1))

if os.getenv("SERVE_FRONTEND", "true").lower() == "true":
    build_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "build")
    build_dir = os.path.normpath(build_dir)
    if os.path.isdir(build_dir):
        # Mount static files for assets
        base_app.mount("/assets", StaticFiles(directory=os.path.join(build_dir, "assets")), name="assets")
        # Mount static files for locales
        base_app.mount("/locales", StaticFiles(directory=os.path.join(build_dir, "locales")), name="locales")

        # SPA fallback for all other routes
        @base_app.middleware("http")
        async def spa_fallback(request: Request, call_next):
            """Handle SPA routing fallback for non-API requests.
            
            Routes API and Socket.IO requests to their handlers, serves SPA for all other routes.
            
            Args:
                request: Incoming HTTP request
                call_next: Next middleware in chain
                
            Returns:
                Response from next middleware or SPA index.html

            """
            # Let API routes, Socket.IO, and already-mounted static directories handle their requests
            if (
                request.url.path.startswith("/api/")
                or request.url.path.startswith("/socket.io/")
                or request.url.path.startswith("/mcp/")
                or request.url.path.startswith("/health")
                or request.url.path.startswith("/assets/")
                or request.url.path.startswith("/locales/")
            ):
                return await call_next(request)
            
            # Serve any existing file under the built frontend directory directly
            # This avoids having to maintain a hard-coded allowlist and fixes cases like /forge-icon.png
            requested_path = request.url.path.lstrip("/")
            candidate_path = os.path.normpath(os.path.join(build_dir, requested_path))

            # Prevent path traversal outside of build_dir
            if os.path.commonpath([candidate_path, build_dir]) == os.path.normpath(build_dir):
                if os.path.isfile(candidate_path):
                    from fastapi.responses import FileResponse
                    return FileResponse(candidate_path)

            # For all other requests (HTML, SPA routes), serve the SPA
            spa_files = SPAStaticFiles(directory=build_dir, html=True)
            return await spa_files.get_response("index.html", request.scope)

    else:
        import logging

        logging.getLogger("forge").info(
            f"SPA build not found at {build_dir}; skipping static mount. Set SERVE_FRONTEND=true and build frontend to enable.",
        )
app = socketio.ASGIApp(sio, other_asgi_app=base_app)
