# Forge

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![mypy: checked](https://img.shields.io/badge/mypy-checked-2A6DB2.svg)](https://mypy-lang.org/)
[![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Forge** is an open-source AI coding platform built for long-running, autonomous coding sessions.
It pairs a **Textual TUI** with a **FastAPI + Socket.IO** backend and ships with
event-sourced session resilience, configurable safety & budget controls, and a 23-tool agent engine.

---

## Highlights

| | Feature | Details |
|---|---|---|
| 🧠 | **Agent Engine** | CodeAct orchestrator with 23 tools, anti-hallucination system, and task planning |
| 🔁 | **Event-Sourced Sessions** | WAL crash recovery, backpressure-aware streams, full replay |
| 🛡️ | **Safety & Budget** | Circuit breaker, 6-strategy stuck detector, per-task cost caps ($5 default) |
| 🧩 | **12 Context Condensers** | Smart, LLM, semantic, amortized, attention, sliding window, and more |
| 🌐 | **Multi-LLM** | OpenAI, Anthropic, Google Gemini — swap with one config change |
| 🔌 | **MCP Integration** | Model Context Protocol client for external tool servers |
| 🎭 | **Playbooks** | 19 built-in playbooks for common workflows |
| 🌳 | **Structure-Aware Editing** | Tree-sitter parsing across 45+ languages |
| 📡 | **Real-Time Streaming** | Socket.IO with reconnection, room management, event namespacing |
| 🖥️ | **Textual TUI** | Native terminal interface — zero Node.js / browser required |

## Architecture

```
TUI (Textual)  ←→  Server (FastAPI + Socket.IO)
                           ↓
                   AgentController (21 services)
                           ↓
                   Orchestrator Engine (23 tools)
                           ↓
                   EventStream (WAL + backpressure)
                           ↓
                   Memory (12 condensers) + Storage
```

For the full walkthrough, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Quick Start

> **Windows?** Run `.\START_HERE.ps1` at the repo root — it starts the server and TUI.

### Prerequisites

- Python 3.12+
- [Poetry](https://python-poetry.org/docs/#installation)

### Backend

```bash
poetry install
python start_server.py        # http://localhost:3000
```

### TUI (separate terminal)

```bash
python -m backend.tui          # or: forge-tui
```

See [QUICK_START.md](QUICK_START.md) for a more detailed guide.

## Configuration

Runtime configuration loads from `config.toml` and environment variables.
Start from:

- [config.template.toml](config.template.toml) — copy to `config.toml`
- [backend/core/config/README.md](backend/core/config/README.md) — full reference

## Commands

| Command | Purpose |
|---|---|
| `poetry run pytest backend/tests` | Backend tests |
| `python -m backend.tui` | Launch TUI |
| `forge-tui --port 3000` | Launch TUI (script entry) |

## Project Structure

```
backend/
├── controller/     # Agent loop orchestration (21 services)
├── engines/        # Agent engines (orchestrator, auditor, navigator)
├── events/         # Event sourcing, WAL, backpressure
├── memory/         # Context condensers, RAG, vector store
├── server/         # FastAPI app, routes, middleware, Socket.IO
├── storage/        # File, PostgreSQL, SQLite storage
├── tui/            # Textual TUI (screens, widgets, client)
└── core/           # Config, exceptions, schemas, logging
```

## Authentication

HTTP and Socket.IO share the same auth model. See [docs/AUTH.md](docs/AUTH.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, architecture reference, and contribution workflow.

## License

MIT — see [LICENSE](LICENSE).
