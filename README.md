# Forge

> **Forge your software with AI** — The open-source platform for reliable, long-session agentic coding.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.55.0-brightgreen.svg)](pyproject.toml)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](pyproject.toml)

**Forge** is an open-source AI development platform built for **daily use** and **long coding sessions**. It features event-sourced session resilience, structure-aware editing, cost tracking, and production-grade safeguards.

## What's in this repo

- `backend/` — Python backend (FastAPI, asyncio, PostgreSQL optional)
- `frontend/` — React frontend (Vite, Redux Toolkit, TanStack Query)
- `config.template.toml` — All configuration knobs with inline docs

## Quick start

**Prerequisites:** Python 3.12+, Node.js 20+, pnpm

```bash
# 1. Backend
poetry install
python start_server.py

# 2. Frontend (separate terminal)
cd frontend
pnpm install
pnpm run dev
```

Or on Windows: run `START_HERE.ps1` in PowerShell.

**Access:**
- Frontend: http://localhost:3001
- Backend API: http://localhost:3000/api
- Swagger Docs: http://localhost:3000/docs

## Key Features

- **Event-Sourced Sessions** — Reconnect anytime without losing agent state (replay system)
- **12 Context Condensers** — Smart/LLM/semantic/sliding-window strategies for long sessions
- **Structure-Aware Editing** — Tree-sitter integration (45+ languages)
- **Cost Guards** — Per-task budget limits, token tracking, audit logging
- **Circuit Breakers** — Error classification, retry orchestration, stuck detection
- **MCP Integration** — Model Context Protocol for external tool servers
- **PostgreSQL Storage** — Optional DB-backed persistence (file storage default)
- **Single API Key Auth** — `X-Session-API-Key` header (no user/password complexity)

## Architecture

```
┌─────────────┐     Socket.IO      ┌──────────────────┐
│   React UI  │◄──────────────────►│   FastAPI Server  │
│  (Vite/RR7) │    (event replay)  │   (listen.py)     │
└─────────────┘                    └────────┬─────────┘
                                            │
                              ┌─────────────┼─────────────┐
                              │             │             │
                       ┌──────▼─────┐ ┌─────▼────┐ ┌─────▼──────┐
                       │ Controller │ │  Storage  │ │   Events   │
                       │ (21 svc)   │ │ (PG/File) │ │ (sourced)  │
                       └──────┬─────┘ └──────────┘ └────────────┘
                              │
                       ┌──────▼─────┐
                       │ Orchestrator│
                       │ (Jinja2     │
                       │  prompts)   │
                       └─────────────┘
```

## Configuration

All settings live in `config.toml` (copy from `config.template.toml`). Key knobs:

| Setting | Default | Description |
|---|---|---|
| `SESSION_API_KEY` | auto-generated | Auth key for all API/WebSocket requests |
| `CONVERSATION_STORE_CLASS` | `FileConversationStore` | Switch to `DatabaseConversationStore` for PG |
| `KB_STORAGE_TYPE` | `file` | `database` for PostgreSQL knowledge base |
| `DEFAULT_QUOTA_PLAN` | `free` | Cost quota tier (`free`/`pro`/`enterprise`/`unlimited`) |

See [config.template.toml](config.template.toml) for the full reference.

## Contributing

We welcome contributions! Please:
1. Fork the repo and create a feature branch
2. Follow existing code patterns (type hints, docstrings)
3. Run `pytest` before submitting a PR
4. Keep PRs focused — one feature/fix per PR

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

MIT License — see [LICENSE](LICENSE)
