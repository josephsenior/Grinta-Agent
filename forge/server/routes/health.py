"""Health and diagnostics endpoints for the Forge server."""

from fastapi import FastAPI

from forge.runtime.utils.system_stats import get_system_info


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
    async def health() -> str:
        """Basic health endpoint returning static OK."""
        return "OK"

    @app.get("/server_info")
    async def get_server_info():
        """Expose system metrics gathered from runtime utilities."""
        return get_system_info()
