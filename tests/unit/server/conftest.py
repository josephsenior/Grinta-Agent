import contextlib

import pytest


@pytest.fixture(autouse=True)
def reset_streamable_session_manager(monkeypatch):
    """Allow FastMCP session manager to be reused across TestClient instances."""
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

    original_run = StreamableHTTPSessionManager.run

    @contextlib.asynccontextmanager
    async def run_with_reset(self):
        async with original_run(self):
            try:
                yield
            finally:
                # Allow the same instance to start again for the next test.
                self._has_started = False

    monkeypatch.setattr(StreamableHTTPSessionManager, "run", run_with_reset)

