"""Static file utilities for serving the Forge single-page application."""

from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope


class SPAStaticFiles(StaticFiles):
    """StaticFiles subclass that falls back to index.html for client-side routing."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        """Serve requested asset, falling back to SPA entrypoint on errors."""
        try:
            return await super().get_response(path, scope)
        except Exception:
            return await super().get_response("index.html", scope)
