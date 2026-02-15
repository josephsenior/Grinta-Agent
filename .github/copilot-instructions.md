# Copilot instructions for Forge

## Big picture architecture
- TUI is Textual (Python) in `backend/tui/`; all network access goes through `ForgeClient` (httpx + socketio). See [ARCHITECTURE.md](ARCHITECTURE.md).
- Backend is FastAPI with Socket.IO; the request stack, session lifecycle, and routes are described in [backend/server/README.md](backend/server/README.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
- The agent loop is centered in `AgentController` and 21 controller services in [backend/controller](backend/controller), with resilience features like circuit breakers and stuck detection documented in [ARCHITECTURE.md](ARCHITECTURE.md).
- Sessions are event sourced via `EventStream` with WAL recovery and backpressure in [backend/events](backend/events); many flows are event-driven rather than direct calls.
- Memory and context management live in [backend/memory](backend/memory) with multiple condenser strategies; orchestrator engine is in [backend/engines/orchestrator](backend/engines/orchestrator).

## Workflows and commands
- Backend dev: `poetry install` then `python start_server.py` (API on :3000); Windows shortcut is `START_HERE.ps1` at repo root. See [README.md](README.md).
- TUI dev: `python -m backend.tui` or `forge-tui` (connects to backend on :3000).
- Backend tests: `poetry run pytest backend/tests` or `make test-unit`; see [backend/README.md](backend/README.md).
- Utility scripts are under [backend/scripts](backend/scripts); use the subfolder README for the exact command (build, verify, setup, dev, database, mcp).

## Project-specific conventions
- Configuration loads from `config.toml` and env vars using class-prefixed names (e.g., `LLM_API_KEY`, `AGENT_...`); see [backend/core/config/README.md](backend/core/config/README.md).
- WebSocket and HTTP use a shared auth model; the single source of truth is [docs/AUTH.md](docs/AUTH.md) (see [backend/README.md](backend/README.md)).
- MCP integration uses cached wrapper tools like `search_components` and `get_component_cached`; see [backend/mcp/README.md](backend/mcp/README.md).

## Integration points and data flow
- Client talks to FastAPI routes and Socket.IO; the server creates a session, then an agent session, then streams actions/observations; see [backend/server/README.md](backend/server/README.md).
- Runtime execution is isolated and action-based; most edits or commands become actions and observations flowing through the event system.
- TUI WebSocket handling is in `ForgeClient` (`backend/tui/client.py`), with events dispatched to screen widgets.

## Where to look for examples
- Controller service patterns: [backend/controller](backend/controller)
- Engine tools and prompts: [backend/engines/orchestrator](backend/engines/orchestrator)
- Event definitions and stream behavior: [backend/events](backend/events)
- TUI screens and widgets: [backend/tui](backend/tui)
