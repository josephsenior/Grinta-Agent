# Forge Architecture

## Overview

Forge is a production-grade AI coding agent system built on a 5-layer architecture, currently optimized for the CodeAct agent (beta launch focus).

### Code Quality
- **144,110 lines of production backend code** (Python)
- **101,417 lines of production frontend code** (TypeScript/TSX)
- **245,527 total lines of production code** (excluding tests)
- **704 Python files** in backend
- **983 frontend files** (584 TSX, 398 TS)
- **Backend average complexity: 3.06** (A-rated) across 8,100 functions/methods
- **Frontend average complexity: 2.21** (A-rated)
- **0% high-complexity functions** (industry-leading)
- See [code-quality.md](code-quality.md) for detailed metrics

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Frontend (React + TypeScript + Redux)         │
│  • 300+ components with modern animations               │
│  • Real-time WebSocket communication                    │
│  • Redux Toolkit + React Query state management         │
│  • Tailwind CSS styling system                          │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  Layer 2: FastAPI Server (32 Route Files)               │
│  • REST API with OpenAPI documentation                  │
│  • WebSocket for real-time updates                      │
│  • Middleware: CORS, Security, Rate Limiting, Caching   │
│  • Request tracing with correlation IDs                 │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  Layer 3: CodeAct Agent (Beta Focus)                    │
│  • Event-driven architecture (EventStream)              │
│  • State machine (INIT→RUNNING→PAUSED→FINISHED)         │
│  • Tool execution (edit, bash, browse, IPython)         │
│  • Circuit breaker for safety                           │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  Layer 4: LLM Abstraction (200+ Models)                 │
│  • LiteLLM integration (30+ providers)                  │
│  • Secure API key management                            │
│  • Feature detection (function calling, caching)        │
│  • Cost tracking and metrics                            │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  Layer 5: Runtime & Execution (Docker Sandbox)          │
│  • RuntimeOrchestrator (acquire/release)                │
│  • Warm/Single-use pools with per-key policies          │
│  • Watchdog for idle/stuck termination                  │
│  • Scaling advisories + Prometheus telemetry            │
└─────────────────────────────────────────────────────────┘
```

## Data Flow: User Request → Agent Response

```
User sends message via Socket.IO
   ↓
Message received by server (forge/server/listen_socket.py)
   ↓
Event published to EventStream
   ↓
AgentController.step() invoked
   ↓
CodeAct agent analyzes state and generates prompt
   ↓
LLM.completion() called via LiteLLM
   ↓
Response parsed into Action (FileEditAction, CmdRunAction, etc.)
   ↓
Action sent to Runtime for execution in Docker sandbox
   ↓
Observation generated from execution result
   ↓
Observation added to State
   ↓
State update event published to EventStream
   ↓
Socket.IO emits update to frontend
   ↓
UI updates in real-time
```

## Core Components Deep Dive

### 1. Provider System (30+ LLM Providers)

**Architecture:**

```
User configures model: "openrouter/gpt-4o"
   ↓
APIKeyManager._extract_provider("openrouter/gpt-4o") → "openrouter"
   ↓
APIKeyManager.get_api_key_for_model() → SecretStr(OPENROUTER_API_KEY)
   ↓
ProviderConfigManager.validate_and_clean_params() 
   → Removes forbidden params (e.g., custom_llm_provider)
   → Validates required params (api_key, model)
   ↓
Environment variables set (OPENROUTER_API_KEY=...)
   ↓
LiteLLM.completion(model="openrouter/gpt-4o", ...)
   ↓
Response + cost tracking + metrics
```

**Supported Providers:**

| Provider | Models | Key Prefix | Features |
|----------|--------|------------|----------|
| OpenAI | GPT-4, GPT-5, o3, o4-mini | sk- | Function calling, vision |
| Anthropic | Claude 3.5, 4, 4.5 | sk-ant- | Prompt caching, function calling |
| OpenRouter | 200+ models | sk-or- | Meta-provider, all models |
| xAI | Grok 4, Grok 4 Fast | - | Tool use, 2M context |
| Google | Gemini 2.5 | AIza | Vision, function calling |
| Mistral | Devstral series | mistral- | Code-specific models |
| AWS Bedrock | Claude, Llama, etc. | - | Enterprise deployment |
| Azure OpenAI | GPT-4, GPT-5 | - | Enterprise deployment |
| Ollama | Local models | - | Privacy, offline use |

**Key Files:**
- `forge/core/config/api_key_manager.py` - Secure key management, provider detection
- `forge/core/config/provider_config.py` - 30+ provider configurations with validation rules
- `forge/llm/model_features.py` - Feature detection (function calling, caching, vision)
- `forge/llm/llm.py` - Main LLM class with retry logic, cost tracking
- `forge/llm/utils/batching.py` - LLM request batching for efficiency

### 2. Event-Driven Architecture

**EventStream (Central Pub/Sub Hub):**

```python
# File: Forge/events/event_stream.py

# Publishing events
event_stream.add_event(MessageAction(content="Hello"))
event_stream.add_event(CmdOutputObservation(content="Done"))

# Subscribing to events
async for event in event_stream.subscribe(event_id):
    if isinstance(event, Observation):
        # Process observation
```

**Event Types:**

| Category | Events | Purpose |
|----------|--------|---------|
| Actions | MessageAction, FileEditAction, CmdRunAction, BrowseInteractiveAction | Agent intentions |
| Observations | CmdOutputObservation, FileReadObservation, BrowserObservation | Execution results |
| State | AgentStateChangeEvent | Agent lifecycle |
| Errors | ErrorObservation | Error handling |

#### Typed Event Contracts

- **Versioned Schemas:** All actions and observations now conform to explicit Pydantic schemas in `forge/core/schemas/`. Every payload published to the `EventStream` carries an `EventSchemaV1` header so we can evolve contracts without breaking consumers.
- **Action Models:** `CodeAct` emits canonical action schemas (read/write/edit/run, etc.) complete with metadata (confirmation state, security risk). Consumers can deserialize via `forge.core.schemas.serialization.deserialize_event`.
- **Observation Models:** Runtime responses (command output, file edits, errors) serialize to typed observation schemas with optional command metadata, improving replay/debug tooling.
- **Migration Ready:** `EventVersion` keeps the door open for future schema upgrades. `migrate_schema_version` provides forward/backward compatibility between versions.
- **Shared Tests:** Unit tests in `tests/unit/core/schemas/` guarantee every schema stays aligned with real runtime objects.

#### Telemetry Integration

- **Tool Telemetry:** `ToolTelemetry` ingests action/observation schemas and records structured metrics (Prometheus counters + in-memory ring buffer), giving us consistent plan/verify/execute/observe traces.
- **Middleware Pipeline:** `TelemetryMiddleware` attaches the schema contracts as we step through the plan → verify → execute → observe pipeline, ensuring instrumentation stays in lock-step with event semantics.
- **Diagnostics:** Recorded events include schema snapshots for each invocation, massively reducing time-to-debug when a production run misbehaves.

**Benefits:**
- Decoupled components (agents don't know about UI)
- Real-time updates (WebSocket subscribers)
- Audit trail (all events logged)
- Replay capability (event sourcing)

### 3. Agent System (CodeAct for Beta)

**CodeAct Agent State Machine:**

```
INIT
  ↓ (start)
RUNNING
  ↓ (user pause / safety trigger)
PAUSED
  ↓ (user resume)
RUNNING
  ↓ (task complete / error / user stop)
FINISHED
```

**CodeAct Agent Loop:**

```python
# File: Forge/agenthub/codeact_agent/codeact_agent.py

def step(state: State) -> Action:
    # 1. Analyze current state
    recent_events = state.history[-10:]
    
    # 2. Build prompt with context
    messages = self._get_messages(state)
    
    # 3. Call LLM
    response = self.llm.completion(messages, tools=AVAILABLE_TOOLS)
    
    # 4. Parse action from response
    action = self._parse_action(response)
    
    # 5. Return action for execution
    return action
```

#### Controller Service Layer

To keep the `AgentController` lean and production-focused, the controller delegates key responsibilities to **20 specialized services**:

| Service | Responsibility | Key Files |
|---------|----------------|-----------|
| `LifecycleService` | State tracker setup, event subscriptions, state persistence wiring | `forge/controller/services/lifecycle_service.py` |
| `AutonomyService` | Autonomy level configuration, safety/task validators, circuit-breaker configuration | `forge/controller/services/autonomy_service.py` |
| `TelemetryService` | Tool pipeline assembly, telemetry emission for blocked actions | `forge/controller/services/telemetry_service.py` |
| `RetryService` | Background retry queue orchestration with graceful Redis fallbacks | `forge/controller/services/retry_service.py` |
| `CircuitBreakerService` | Centralizes circuit breaker checks and error/stuck bookkeeping | `forge/controller/services/circuit_breaker_service.py` |
| `StuckDetectionService` | Wraps the Tree-sitter based stuck detector and delegates | `forge/controller/services/stuck_detection_service.py` |
| `ActionService` | Action parsing and validation | `forge/controller/services/action_service.py` |
| `ActionExecutionService` | Action execution coordination | `forge/controller/services/action_execution_service.py` |
| `ObservationService` | Observation logging and metrics prep | `forge/controller/services/observation_service.py` |
| `RecoveryService` | Exception classification, retries, recovery events | `forge/controller/services/recovery_service.py` |
| `ConfirmationService` | Replay/live action sourcing, autonomy policy | `forge/controller/services/confirmation_service.py` |
| `PendingActionService` | Track pending actions and timeouts | `forge/controller/services/pending_action_service.py` |
| `IterationService` | Iteration management and tracking | `forge/controller/services/iteration_service.py` |
| `IterationGuardService` | Iteration/budget ceilings, graceful shutdown | `forge/controller/services/iteration_guard_service.py` |
| `StepGuardService` | Per-step circuit breaker and stuck detection hooks | `forge/controller/services/step_guard_service.py` |
| `StepPrerequisiteService` | Step prerequisite validation | `forge/controller/services/step_prerequisite_service.py` |
| `BudgetGuardService` | Budget tracking and enforcement | `forge/controller/services/budget_guard_service.py` |
| `SafetyService` | Safety validation and checks | `forge/controller/services/safety_service.py` |
| `StateTransitionService` | State machine transitions | `forge/controller/services/state_transition_service.py` |
| `DelegateService` | Delegate spawn/teardown and bookkeeping | `forge/controller/services/delegate_service.py` |

`AgentController` composes these services in `__init__`, so new production safeguards can be added without expanding the controller's surface area. When integrating new behavior, prefer creating a service over extending the controller directly.

##### Controller Health Snapshot (New)

To avoid digging through logs when a run misbehaves, Forge now exposes a consolidated controller health snapshot at `/api/monitoring/controller/{sid}/health`. The endpoint introspects the live `AgentController` and reports:

- core agent state (current `AgentState`, last error, iteration & budget usage vs. their limits)
- safety services (`RetryService`, `CircuitBreakerService`, `StuckDetectionService`) including pending retries and breaker counters
- event-stream backpressure metrics for the session’s `EventStream`
- warnings array (e.g., `iteration_limit_reached`, `retry_pending`, `stuck_detector_triggered`)

This endpoint powers dashboards/alerts and mirrors the prompt-optimization health snapshot so operators can inspect safeguards across both tiers.

##### Runtime / Process Manager Health (New)

Under the hood, every runtime shell registers long-running processes with `ProcessManager`. We now expose the manager’s telemetry (active processes, forced kills, lifetime stats) through the monitoring API so production ops can detect sandboxes that leak or get stuck. Each controller health snapshot includes runtime/process warnings when available, and `/api/monitoring/processes/health` returns a global view (see Runtime section).

Optional middlewares can be toggled via `agent_config`:

- `enable_planning_middleware` adds the `PlanningMiddleware`, which inspects tasks before execution and surfaces a complexity score for the task tracker.
- `enable_reflection_middleware` adds the `ReflectionMiddleware`, invoking self-checks before edits/commands (honoring `enable_reflection`).

**Available Actions:**
- `FileEditAction` - Edit files with structure-aware parsing
- `CmdRunAction` - Execute shell commands
- `IPythonRunCellAction` - Run Python code
- `BrowseInteractiveAction` - Browser automation
- `MessageAction` - Communicate with user
- `AgentFinishAction` - Complete task

### 4. Security & Sandboxing

**Docker-Based Isolation:**

```
Agent action (untrusted)
   ↓
Action execution server validates
   ↓
Executed in Docker container
   ↓
File system isolated
   ↓
Network access controlled
   ↓
Result returned safely
```

**Security Layers:**
1. **Risk Assessment** - AI-powered analysis of commands (`forge/security/analyzer.py`)
2. **Sandbox Execution** - Docker container isolation with security hardening
3. **Input Validation** - Command injection prevention, path traversal protection
4. **Rate Limiting** - Prevent abuse (Redis-backed or in-memory)
5. **Cost Quotas** - Budget protection with multiple plan tiers
6. **JWT Authentication** - Optional token-based authentication with RBAC
7. **Secrets Management** - Encryption at rest for sensitive data
8. **Circuit Breakers** - Protection against cascading failures
9. **Resource Quotas** - Per-user resource limits
10. **Security Headers** - CSP, HSTS, X-Frame-Options, etc.

### 5. Monitoring System (Production-Grade)

**Grafana Dashboards (3):**

| Dashboard | Purpose | Key Metrics |
|-----------|---------|-------------|
| llm-performance.json | LLM monitoring | Latency (p50/p90/p95), tokens, costs |
| system-metrics.json | System health | CPU, memory, active conversations |
| error-tracking.json | Error monitoring | Error rates, failure patterns |

**Prometheus Metrics (30+):**

```
# Runtime & Guardrail highlights
forge_runtime_watchdog_watched{kind="docker"}    # Live sandboxes by kind
forge_runtime_pool_idle_reclaim_total            # TTL-driven warm reclaims
forge_runtime_pool_eviction_total                # Capacity evictions
forge_runtime_scaling_signals_overprovision      # Idle-reclaim spikes
forge_runtime_scaling_signals_capacity_exhausted # Eviction spikes
metasop_guardrail_concurrency_total              # Active step concurrency
metasop_guardrail_concurrency_peak               # Peak concurrency
metasop_guardrail_runtime_avg_ms                 # Avg per-step runtime
```

**Alerting Rules (6):**
1. High error rate (>5%)
2. Slow response time (p95 >2s)
3. Low cache hit rate (<30%)
4. Service down
5. High retry rate (>20%)
6. High token usage

**Frontend Monitoring (7 Components):**
- `live-metrics-cards.tsx` - Real-time metrics display
- `autonomous-monitor.tsx` - Agent activity monitoring
- `risk-level-chart.tsx` - Security risk visualization
- `safety-score-gauge.tsx` - Safety metrics
- `enhanced-audit-trail.tsx` - Action history
- `command-blocking-card.tsx` - Blocked actions
- `animated-alert-banner.tsx` - Alert notifications

### 6. MCP (Model Context Protocol) Integration

**File:** `forge/server/routes/mcp.py`

**Features:**
- FastMCP server implementation
- GitHub/Bitbucket/GitLab integrations via MCP
- Marketplace support (shadcn-ui MCP server)
- Tool registration and discovery
- SSE and HTTP transport support
- Stateless HTTP mode for scalability

**Integration Points:**
- MCP tools available to agents
- External tool server connectivity
- Protocol-compliant tool execution

### 7. HTTP Caching & Compression

**File:** `forge/server/middleware/compression.py`

**Features:**
- ETag generation for cache validation
- Cache-Control headers (static assets: long TTL, APIs: configurable)
- Compression (gzip/brotli)
- Conditional requests (304 Not Modified)
- Multi-layer caching (L1 in-memory + L2 Redis)

**Cache Strategy:**
```python
# Static assets (JS, CSS, images)
Cache-Control: public, max-age=31536000, immutable

# API endpoints (GET requests)
Cache-Control: public, max-age=60, must-revalidate
ETag: "hash-of-response"

# Dynamic content
Cache-Control: no-cache, no-store, must-revalidate
```

## Technology Stack

### Backend
- **Framework:** FastAPI (async, high performance)
- **Server:** Uvicorn with httptools (production: gunicorn with UvicornWorker)
- **Real-time:** Socket.IO (Python socketio library)
- **LLM Integration:** LiteLLM (200+ models, 30+ providers)
- **Database:** SQLAlchemy (async) with conversation storage
- **Containerization:** Docker (with Kubernetes support)
- **Monitoring:** Prometheus + Grafana (3 dashboards, 30+ metrics)
- **Logging:** Structured JSON logging with request IDs
- **MCP Integration:** FastMCP server for Model Context Protocol
- **Entry Point:** `forge/server/__main__.py` → `forge.server.listen:app`
- **Default Port:** 3000 (configurable via `port` environment variable)
- **API Routes:** 32 route modules covering all functionality
- **Middleware:** 14 middleware components (auth, rate limiting, caching, etc.)

### Frontend
- **Framework:** React 18 with TypeScript
- **State:** Redux Toolkit + React Query
- **Styling:** Tailwind CSS
- **Real-time:** Socket.IO client (socket.io-client)
- **Icons:** Lucide React
- **Animations:** Framer Motion
- **Build:** Vite
- **Dev Server:** Port 5173 (Vite default)
- **Production:** Served from backend on port 3000

### Infrastructure
- **Runtime:** Docker containers
- **Caching:** Redis (optional, in-memory fallback)
- **Metrics:** Prometheus (pull-based)
- **Dashboards:** Grafana
- **Logging:** JSON logs with request IDs

## Configuration

**Environment Variables (100+):**

Key configurations:
```bash
# LLM
LLM_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...

# Database
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# Monitoring
LOG_LEVEL=INFO
LOG_JSON=true
ENABLE_MONITORING=true

# Security
SECRET_KEY=...
ALLOWED_ORIGINS=http://localhost:3000

# Features (Beta)
ENABLE_METASOP=false
ENABLE_ACE=true
ENABLE_BROWSER=true
```

See [Configuration Guide](./configuration.md) for complete reference.

## Scaling Considerations

**Current (Production-Ready):**
- Multi-worker support (gunicorn with UvicornWorker)
- SQLite or PostgreSQL with connection pooling
- Multi-layer caching (L1 in-memory + L2 Redis)
- Redis-backed rate limiting and quotas
- Handles: 1,000-10,000 concurrent users

**Scaling Capabilities:**
- Horizontal scaling (multiple server instances)
- Redis for distributed caching and rate limiting
- Database read replicas (connection pooling ready)
- Load balancer support
- Kubernetes runtime support
- Handles: 10,000+ users with proper infrastructure

## References

- [Getting Started](./GETTING_STARTED.md) - Quick start guide
- [API Reference](./api-reference.md) - Complete API documentation
- [Monitoring Guide](./monitoring.md) - Monitoring and observability
- [Troubleshooting](./troubleshooting.md) - Common issues
- [Beta Launch Strategy](./beta-launch-strategy.md) - Beta configuration

## Component Details

For deep dives into specific components:
- **LLM System:** See `Forge/llm/README.md`
- **CodeAct Agent:** See `Forge/agenthub/codeact_agent/README.md`
- **Security:** See `Forge/security/README.md`
- **Frontend:** See `frontend/README.md`

## API Routes (32 Route Files)

The FastAPI server includes **32 route modules** covering all backend functionality:

| Route | Purpose | Endpoints |
|-------|---------|-----------|
| `activity.py` | Activity feed and timeline | `/api/activity/*` |
| `analytics.py` | Usage analytics and metrics | `/api/analytics/*` |
| `auth.py` | Authentication endpoints | `/api/auth/*` |
| `billing.py` | Payment processing and subscriptions | `/api/billing/*` |
| `conversation.py` | Conversation management | `/api/conversations/*` |
| `dashboard.py` | Dashboard data and quick stats | `/api/dashboard/*` |
| `database_connections.py` | Database connection management | `/api/database/*` |
| `examples.py` | Example code and demos | `/api/examples/*` |
| `feedback.py` | User feedback collection | `/api/feedback/*` |
| `files.py` | File operations and workspace | `/api/files/*` |
| `git.py` | Git integration | `/api/git/*` |
| `global_export.py` | Data export functionality | `/api/export/*` |
| `health.py` | Health check endpoints | `/api/health/*` |
| `knowledge_base.py` | Knowledge base management | `/api/knowledge/*` |
| `manage_conversations.py` | Conversation administration | `/api/conversations/*` |
| `mcp.py` | Model Context Protocol server | `/mcp/*` |
| `memory.py` | Memory and vector storage | `/api/memory/*` |
| `metasop.py` | Multi-agent orchestration | `/api/metasop/*` |
| `metrics_expansion.py` | Expanded metrics collection | `/api/monitoring/metrics/expanded` |
| `monitoring.py` | System monitoring and health | `/api/monitoring/*` |
| `notifications.py` | User notifications | `/api/notifications/*` |
| `profile.py` | User profile and statistics | `/api/profile/*` |
| `prompt_optimization.py` | Prompt optimization | `/api/optimization/*` |
| `prompts.py` | Prompt management | `/api/prompts/*` |
| `public.py` | Public API endpoints | `/api/public/*` |
| `search.py` | Global search across resources | `/api/search/*` |
| `secrets.py` | Secrets management | `/api/secrets/*` |
| `security.py` | Security features | `/api/security/*` |
| `settings.py` | User settings | `/api/settings/*` |
| `slack.py` | Slack integration | `/api/slack/*` |
| `snippets.py` | Code snippets | `/api/snippets/*` |
| `templates.py` | Template management | `/api/templates/*` |
| `trajectory.py` | Agent trajectory tracking | `/api/trajectory/*` |
| `user_management.py` | User administration | `/api/users/*` |

## Middleware Stack (14 Middleware Components)

The server includes a comprehensive middleware pipeline:

| Middleware | Purpose | File |
|------------|---------|------|
| `LocalhostCORSMiddleware` | CORS handling with localhost support | `middleware_core.py` |
| `AuthMiddleware` | JWT authentication (optional) | `middleware/auth.py` |
| `RequestIDMiddleware` | Request ID tracking | `middleware/request_id.py` |
| `RequestTracingMiddleware` | Request tracing and correlation | `middleware/request_tracing.py` |
| `CompressionMiddleware` | Response compression (gzip/brotli) | `middleware/compression.py` |
| `SecurityHeadersMiddleware` | Security headers (CSP, HSTS, etc.) | `middleware/security_headers.py` |
| `CSRFProtection` | CSRF token validation | `middleware/security_headers.py` |
| `CostQuotaMiddleware` | Cost-based quota enforcement | `middleware/cost_quota.py` |
| `ResourceQuotaMiddleware` | Resource quota management | `middleware/resource_quota.py` |
| `RateLimiter` | Rate limiting (Redis or in-memory) | `middleware/rate_limiter.py` |
| `CircuitBreakerMiddleware` | Circuit breaker pattern | `middleware/circuit_breaker.py` |
| `RequestObservabilityMiddleware` | Request observability | `middleware/observability.py` |
| `RequestMetricsMiddleware` | Request metrics collection | `middleware/request_metrics.py` |
| `RequestSizeLoggingMiddleware` | Request size logging | `middleware/request_size.py` |
| `SocketIOConnectionManager` | Socket.IO connection management | `middleware/socketio_connection_manager.py` |

## Event Pipeline Hardening

- EventStream now enqueues first, with async durability via `DurableEventWriter`; secrets are masked recursively with precompiled patterns.
- EventServiceServer provides in‑process publish/subscribe/replay with RPC metrics for totals, failures, and latency.

## Production Enhancements (All 18 Complete)

All recommended backend enhancements have been implemented and integrated:

**Infrastructure:**
- ✅ Production worker configuration (gunicorn)
- ✅ Database health checks
- ✅ JWT authentication with RBAC
- ✅ Resource quota management
- ✅ Circuit breaker pattern
- ✅ Pagination utilities
- ✅ Multi-layer caching (L1 + L2 Redis)
- ✅ Graceful shutdown
- ✅ Enhanced error responses

**Advanced Features:**
- ✅ Retry logic with exponential backoff
- ✅ Input validation and sanitization
- ✅ Secrets management (encryption at rest)
- ✅ Socket.IO connection management (fully integrated)
- ✅ LLM API request batching
- ✅ Docker sandbox security hardening (fully integrated)
- ✅ Database connection pooling
- ✅ Comprehensive monitoring metrics (fully integrated)
- ✅ Developer guides and runbooks

See [COMPLETE_IMPLEMENTATION_REPORT.md](COMPLETE_IMPLEMENTATION_REPORT.md) for full details.

## Backend Folder-by-Folder Analysis

This section provides a comprehensive breakdown of each major folder in the backend, detailing their purpose, key components, and relationships.

### `forge/agenthub/` - Agent Implementations

**Purpose:** Contains all agent implementations that can be used by the framework.

**Structure:**
- **`codeact_agent/`** (56 files) - Primary agent for beta launch
  - Core agent logic with 29 classes/functions
  - 19 Jinja2 prompt templates (system prompts, user prompts, examples)
  - Tools: bash, file editing, IPython, browser, database, task tracking
  - Features: anti-hallucination system, memory manager, planner, safety validator
  - Advanced tools: ultimate_editor, atomic_refactor, llm_based_edit
  
- **`browsing_agent/`** (8 files) - Web browsing specialist
  - Browser automation and web interaction
  - State tracking for browsing sessions
  
- **`readonly_agent/`** (17 files) - Read-only code exploration
  - File reading, searching, semantic search
  - Code exploration without modifications
  
- **`loc_agent/`** (9 files) - Lines of Code analysis agent
  - Code structure exploration
  - Graph-based code analysis
  
- **`visualbrowsing_agent/`** (3 files) - Visual web browsing
  - Screenshot-based web interaction
  
- **`dummy_agent/`** (2 files) - Testing/mock agent

**Key Features:**
- Multi-agent delegation support
- Tool-based action system
- Prompt optimization integration
- Memory and context management

### `forge/core/` - Core Framework Components

**Purpose:** Fundamental building blocks used throughout the system.

**Structure:**
- **`config/`** (20 files) - Configuration management
  - `forge_config.py` - Main configuration class (102 functions/classes)
  - `llm_config.py` - LLM configuration (55 functions/classes)
  - `agent_config.py` - Agent settings (60 functions/classes)
  - `api_key_manager.py` - Secure API key handling
  - `provider_config.py` - 30+ LLM provider configurations
  - `mcp_config.py` - Model Context Protocol config
  - `security_config.py`, `sandbox_config.py`, `runtime_pool_config.py`
  - Environment variable loading, TOML file support
  
- **`cache/`** (4 files) - Caching layer
  - `redis_cache.py` - Redis-backed caching
  - `async_smart_cache.py` - Async caching with TTL
  - `smart_config_cache.py` - Configuration caching
  
- **`schemas/`** (6 files) - Data schemas
  - `actions.py` - Action type definitions
  - `observations.py` - Observation types
  - `serialization.py` - Event serialization
  - `base.py`, `enums.py` - Base types
  
- **`utils/`** (4 files) - Utility functions
  - `retry.py` - Retry logic with exponential backoff
  - Test utilities for metrics and retry
  
- **`rollback/`** (2 files) - Rollback management
  - `rollback_manager.py` - State rollback functionality

**Key Files:**
- `logger.py` (54 functions) - Structured logging system
- `message.py` (23 functions) - Message handling
- `exceptions.py` (58 functions) - Exception hierarchy
- `tracing.py` (18 functions) - Distributed tracing
- `main.py` (28 functions) - Core initialization

**Total:** 49 files with 1,129 classes/functions

### `forge/events/` - Event-Driven Architecture

**Purpose:** Event streaming, serialization, and event store implementations.

**Structure:**
- **`action/`** (10 files) - Action event types
  - `action.py` - Base action class
  - `commands.py` - Command execution actions
  - `files.py` - File operation actions
  - `browse.py` - Browser actions
  - `agent.py` - Agent lifecycle actions
  - `message.py` - Message actions
  - `mcp.py` - MCP protocol actions
  
- **`observation/`** (17 files) - Observation event types
  - `observation.py` - Base observation class
  - `commands.py` - Command output observations
  - `files.py` - File operation results
  - `browse.py` - Browser output
  - `error.py` - Error observations
  - `success.py` - Success confirmations
  - `delegate.py` - Delegate execution results
  
- **`serialization/`** (5 files) - Event serialization
  - `event.py` - Event serialization (40 functions)
  - `action.py` - Action serialization (18 functions)
  - `observation.py` - Observation serialization (27 functions)
  
- **Core Event Files:**
  - `event_stream.py` (42 functions) - Pub/Sub event stream
  - `event_store.py` (23 functions) - Persistent event storage
  - `event.py` (32 functions) - Base event class
  - `durable_writer.py` (12 functions) - Durable event writing
  - `nested_event_store.py` (11 functions) - Nested event storage

**Total:** 39 files with 505 classes/functions

### `forge/storage/` - Data Persistence Layer

**Purpose:** Storage abstractions for files, conversations, users, and settings.

**Structure:**
- **`data_models/`** (11 files) - Data models
  - `user.py` - User authentication model
  - `conversation_metadata.py` - Conversation tracking
  - `code_snippet.py` - Code snippet storage
  - `prompt_template.py` - Template management
  - `knowledge_base.py` - Knowledge base models
  - `slack_integration.py` - Slack integration data
  - `user_secrets.py` - Encrypted secrets storage
  
- **`conversation/`** (4 files) - Conversation storage
  - `conversation_store.py` - Conversation persistence
  - `conversation_validator.py` - Validation logic
  - `file_conversation_store.py` - File-based storage
  
- **`user/`** (2 files) - User management
  - `user_store.py` - User storage interface
  - `file_user_store.py` - File-based user storage
  
- **`secrets/`** (2 files) - Secrets management
  - `secrets_store.py` - Secrets interface
  - `file_secrets_store.py` - Encrypted file storage
  
- **`settings/`** (2 files) - Settings storage
  - `settings_store.py` - Settings interface
  - `file_settings_store.py` - File-based settings
  
- **Storage Backends:**
  - `local.py` - Local filesystem storage
  - `s3.py` - Amazon S3 storage (4 classes/functions)
  - `google_cloud.py` - Google Cloud Storage
  - `memory.py` - In-memory storage
  - `web_hook.py` - Webhook integration
  - `batched_web_hook.py` - Batched webhook operations
  
- **Utilities:**
  - `db_pool.py` - Database connection pooling (2 classes)
  - `files.py` - File operations
  - `knowledge_base_store.py` - Knowledge base storage

**Total:** 33 files with 79 classes/functions

### `forge/server/` - FastAPI Web Server

**Purpose:** HTTP/WebSocket server, API routes, and middleware.

**Structure:**
- **`routes/`** (28 files) - API route modules
  - `conversation.py` - Conversation management
  - `files.py` - File operations
  - `auth.py` - Authentication
  - `monitoring.py` - System monitoring
  - `mcp.py` - Model Context Protocol server
  - `metasop.py` - Multi-agent orchestration
  - `prompt_optimization.py` - Prompt optimization API
  - `memory.py` - Memory management
  - `knowledge_base.py` - Knowledge base API
  - `security.py` - Security features
  - `settings.py` - User settings
  - `slack.py` - Slack integration
  - `analytics.py` - Usage analytics
  - `trajectory.py` - Agent trajectory tracking
  - And 14 more route modules...
  
- **`middleware/`** (14 files) - Middleware components
  - `auth.py` - JWT authentication
  - `rate_limiter.py` - Rate limiting (Redis-backed)
  - `cost_quota.py` - Cost quota enforcement
  - `resource_quota.py` - Resource limits
  - `circuit_breaker.py` - Circuit breaker pattern
  - `compression.py` - Response compression
  - `security_headers.py` - Security headers (CSP, HSTS)
  - `request_id.py` - Request ID tracking
  - `request_tracing.py` - Distributed tracing
  - `observability.py` - Request observability
  - `request_metrics.py` - Metrics collection
  - `request_size.py` - Request size logging
  - `socketio_connection_manager.py` - Socket.IO management
  
- **Core Server Files:**
  - `app.py` - FastAPI application factory (682 lines)
  - `listen.py` - WebSocket server
  - `session/` - Session management
  - `shared.py` - Shared server state

**Total:** 95 files (92 Python files)

### `forge/controller/` - Agent Control System

**Purpose:** Agent lifecycle management, state transitions, and orchestration.

**Structure:**
- **`services/`** (24 files) - Controller services
  - `lifecycle_service.py` - Agent lifecycle management
  - `autonomy_service.py` - Autonomy level control
  - `action_service.py` - Action parsing/validation
  - `action_execution_service.py` - Action execution
  - `observation_service.py` - Observation handling
  - `recovery_service.py` - Error recovery
  - `retry_service.py` - Retry logic
  - `circuit_breaker_service.py` - Circuit breaker
  - `stuck_detection_service.py` - Stuck detection
  - `budget_guard_service.py` - Budget enforcement
  - `iteration_service.py` - Iteration tracking
  - `iteration_guard_service.py` - Iteration limits
  - `step_guard_service.py` - Step-level guards
  - `safety_service.py` - Safety validation
  - `confirmation_service.py` - User confirmation
  - `pending_action_service.py` - Pending action tracking
  - `delegate_service.py` - Multi-agent delegation
  - `telemetry_service.py` - Telemetry collection
  - `state_transition_service.py` - State machine
  - `step_prerequisite_service.py` - Prerequisites
  
- **Core Controller Files:**
  - `agent_controller.py` - Main controller orchestrator
  - `agent.py` - Agent base class
  - `autonomy.py` - Autonomy logic
  - `checkpoint_manager.py` - State checkpoints
  - `circuit_breaker.py` - Circuit breaker implementation
  - `error_recovery.py` - Error recovery strategies
  - `health.py` - Health monitoring
  - `progress_tracker.py` - Progress tracking
  - `safety_validator.py` - Safety checks
  - `stuck.py` - Stuck detection
  - `tool_pipeline.py` - Tool execution pipeline
  - `tool_telemetry.py` - Tool metrics

**Total:** 24 service files + 12 core controller files

### `forge/runtime/` - Execution Environment

**Purpose:** Runtime environments for executing agent actions (Docker, Kubernetes, Local, Remote).

**Structure:**
- **`impl/`** - Runtime implementations
  - `docker/docker_runtime.py` - Docker container runtime
  - `kubernetes/kubernetes_runtime.py` - Kubernetes runtime
  - `local/local_runtime.py` - Local execution
  - `remote/remote_runtime.py` - Remote execution
  - `cli/cli_runtime.py` - CLI runtime
  - `action_execution/action_execution_client.py` - Action client
  
- **`plugins/`** - Runtime plugins
  - `jupyter/` - Jupyter notebook support
  - `agent_skills/` - Agent skill plugins
    - `file_editor/` - File editing tools
    - `file_ops/` - File operations
    - `file_reader/` - File reading
    - `repo_ops/` - Repository operations
    - `database/` - Database tools
  - `vscode/` - VS Code integration
  
- **Core Runtime Files:**
  - `base.py` - Runtime interface
  - `action_execution_server.py` - Action execution server
  - `process_manager.py` - Process management
  - `runtime_orchestrator.py` - Runtime orchestration

**Total:** 89 files (74 Python files)

### `forge/llm/` - LLM Integration

**Purpose:** Language model abstraction supporting 200+ models from 30+ providers.

**Structure:**
- `llm.py` - Main LLM class with retry logic
- `async_llm.py` - Async LLM wrapper
- `streaming_llm.py` - Streaming support
- `retry_mixin.py` - Retry logic mixin
- `debug_mixin.py` - Debug logging
- `metrics.py` - Cost and latency tracking
- `model_features.py` - Feature detection (function calling, caching, vision)
- `fn_call_converter.py` - Function calling conversion
- `bedrock.py` - AWS Bedrock support
- `llm_utils.py` - Utility functions
- `llm_registry.py` - Model registry
- `cost_tracker.py` - Cost tracking
- `tool_names.py`, `tool_types.py` - Tool definitions

**Key Features:**
- 200+ models supported via LiteLLM
- 30+ provider configurations
- Secure API key management
- Feature detection (function calling, prompt caching, vision)
- Cost tracking and metrics
- Retry logic with exponential backoff
- Streaming support

### `forge/integrations/` - External Integrations

**Purpose:** Third-party service integrations (GitHub, GitLab, Bitbucket, Slack).

**Structure:**
- **`github/`** (9 files) - GitHub integration
  - `github_service.py` - Main GitHub service
  - `service/` - GitHub API clients
    - `repos.py` - Repository operations
    - `branches_prs.py` - Branch and PR management
    - `prs.py` - Pull request operations
    - `features.py` - Feature detection
    - `resolver.py` - Issue resolver
  
- **`gitlab/`** (8 files) - GitLab integration
  - `gitlab_service.py` - Main GitLab service
  - `service/` - GitLab API clients
  
- **`bitbucket/`** (7 files) - Bitbucket integration
  - `bitbucket_service.py` - Main Bitbucket service
  - `service/` - Bitbucket API clients
  
- **`vscode/`** (14 files) - VS Code extension support
  - TypeScript/JavaScript files
  - Extension configuration
  
- **`templates/`** (23 files) - Integration templates
  - Jinja2 templates for various integrations
  
- **Core Integration Files:**
  - `provider.py` - Integration provider abstraction
  - `service_types.py` - Service type definitions (20 classes)
  - `slack_client.py` - Slack client
  - `utils.py` - Integration utilities
  - `protocols/http_client.py` - HTTP client protocol

**Total:** 24 files with 45 classes/functions

### `forge/memory/` - Memory System

**Purpose:** Short-term history, memory condensation, and vector storage.

**Structure:**
- `memory.py` - Main memory interface
- `conversation_memory.py` - Conversation memory
- `enhanced_context_manager.py` - Context management
- `enhanced_vector_store.py` - Vector storage
- `cloud_vector_store.py` - Cloud vector storage
- `view.py` - Memory views
- **`condenser/`** (15 files) - Memory condensation
  - Condenses long conversations into summaries
  - Chunk-based summarization
  - LLM-powered condensation

**Features:**
- Short-term history filtering
- Memory condensation for long conversations
- Vector storage for semantic search
- Context window management

### `forge/metasop/` - Multi-Agent Orchestration

**Purpose:** MetaGPT-inspired orchestration layer for multi-agent workflows.

**Structure:**
- **`ace/`** - ACE Framework (Adaptive Context Engineering)
  - `ace_framework.py` - Main framework
  - `context_playbook.py` - Context playbooks
  - `curator.py` - Context curation
  - `generator.py` - Context generation
  - `reflector.py` - Reflection logic
  - `models.py` - Data models
  - `prompts.py` - Prompt templates
  
- **`core/`** - Core orchestration
  - `execution.py` - Step execution
  - `engines.py` - Execution engines
  - `context.py` - Context management
  - `artifacts.py` - Artifact handling
  - `profile.py` - Agent profiles
  - `reporting.py` - Reporting
  
- **`profiles/`** - Agent role profiles
  - `architect.yaml` - Architect role
  - `engineer.yaml` - Engineer role
  - `product_manager.yaml` - PM role
  - `qa.yaml` - QA role
  - `ui_designer.yaml` - UI Designer role
  
- **`sops/`** - Standard Operating Procedures
  - `feature_delivery.yaml` - Feature delivery SOP
  - `feature_delivery_with_ui.yaml` - UI feature delivery
  
- **Core Files:**
  - `orchestrator.py` - Main orchestrator
  - `router.py` - Agent routing
  - `remediation.py` - Error remediation
  - `retry_service.py` - Retry logic
  - `guardrail_service.py` - Guardrails
  - `qa_service.py` - Quality assurance
  - `budget_monitor_service.py` - Budget monitoring

**Total:** 110 files (88 Python files)

### `forge/prompt_optimization/` - Prompt Optimization

**Purpose:** A/B testing and evolution of prompts and tool descriptions.

**Structure:**
- `optimizer.py` - Main optimizer
- `evolver.py` - Prompt evolution
- `tool_optimizer.py` - Tool-specific optimization
- `tracker.py` - Performance tracking
- `history_store.py` - History storage
- `performance_analytics.py` - Analytics
- `registry.py` - Variant registry
- `storage.py` - Storage backend
- **`advanced/`** (6 files) - Advanced strategies
  - `hierarchical.py` - Hierarchical optimization
  - `multi_objective.py` - Multi-objective optimization
  - `context_aware.py` - Context-aware optimization
  - `strategy_manager.py` - Strategy management
- **`realtime/`** (8 files) - Real-time optimization
  - `live_optimizer.py` - Live optimization
  - `hot_swapper.py` - Hot-swapping variants
  - `streaming_engine.py` - Streaming optimization
  - `websocket_server.py` - WebSocket server

**Features:**
- A/B testing of prompt variants
- LLM-powered prompt evolution
- Tool-specific optimization
- Real-time variant swapping
- Performance analytics

### `forge/resolver/` - Issue Resolver

**Purpose:** Automated GitHub/GitLab/Bitbucket issue resolution.

**Structure:**
- `issue_resolver.py` - Main resolver
- `resolve_issue.py` - Issue resolution logic
- `send_pull_request.py` - PR creation
- `resolver_output.py` - Output formatting
- **`interfaces/`** - Git provider interfaces
  - `github.py` - GitHub interface
  - `gitlab.py` - GitLab interface
  - `bitbucket.py` - Bitbucket interface
  - `issue.py` - Issue model
- **`patching/`** - Patch management
  - `patch.py` - Patch creation
  - `apply.py` - Patch application
  - `snippets.py` - Code snippets
- **`prompts/`** - Resolution prompts
  - `resolve/` - Resolution templates
  - `guess_success/` - Success detection
  - `repo_instructions/` - Repository instructions

**Total:** 37 files (19 Python files)

### `forge/mcp_client/` - Model Context Protocol Client

**Purpose:** MCP client for connecting to external MCP servers.

**Structure:**
- `client.py` - MCP client implementation
- `tool.py` - Tool wrapper
- `utils.py` - Utility functions
- `cache.py` - Result caching
- `wrappers.py` - Tool wrappers
- `error_collector.py` - Error collection

**Features:**
- SSE, HTTP, and stdio transport support
- Tool discovery and registration
- Result caching (10-minute TTL)
- Wrapper tools for common operations

### `forge/security/` - Security Framework

**Purpose:** Security analyzers and risk assessment.

**Structure:**
- `analyzer.py` - Base security analyzer
- `options.py` - Analyzer options
- **`llm_risk/`** - LLM-based risk analyzer
- **`invariant/`** - Invariant security analyzer

**Features:**
- Action risk assessment
- Confirmation mode
- Security event logging
- Custom analyzer support

### `forge/utils/` - Utility Functions

**Purpose:** Shared utility functions across the codebase.

**Structure:**
- `utils.py` - General utilities (2 functions)
- `async_utils.py` - Async utilities (3 functions)
- `retry.py` - Retry logic (10 functions)
- `circuit_breaker.py` - Circuit breaker (6 functions)
- `llm.py` - LLM utilities (7 functions)
- `prompt.py` - Prompt utilities (4 functions)
- `search_utils.py` - Search utilities (2 functions)
- `chunk_localizer.py` - Chunk localization (5 functions)
- `conversation_summary.py` - Conversation summarization (3 functions)
- `http_session.py` - HTTP session management (1 function)
- `metrics_labels.py` - Metrics labeling (1 function)
- `shutdown_listener.py` - Shutdown handling (7 functions)
- `term_color.py` - Terminal colors (2 functions)
- `import_utils.py` - Import utilities (7 functions)

**Total:** 17 files with 62 classes/functions

### `forge/validation/` - Validation

**Purpose:** Input validation and task validation.

**Structure:**
- `task_validator.py` - Task validation (8 functions)

### `forge/services/` - gRPC Services

**Purpose:** gRPC service definitions for event and runtime services.

**Structure:**
- **`event_service/`** - Event service
  - `service.py` - Event service implementation
  - `grpc_server.py` - gRPC server
- **`runtime_service/`** - Runtime service
  - `service.py` - Runtime service implementation
  - `grpc_server.py` - gRPC server
- **`generated/`** - Generated gRPC code
  - Protocol buffer definitions
- **`protos/`** - Protocol definitions
  - `event_service.proto`
  - `runtime_service.proto`
- **`adapters/`** - Service adapters
  - `event_adapter.py` - Event adapter
  - `runtime_adapter.py` - Runtime adapter

**Total:** 20 files (16 Python files, 2 .proto files, 2 .pyi files)

### `forge/audit/` - Audit Logging

**Purpose:** Audit trail and logging.

**Structure:**
- `audit_logger.py` - Audit logger
- `models.py` - Audit models

### `forge/cli/` - Command Line Interface

**Purpose:** CLI tools and TUI interface.

**Structure:**
- `main.py` - CLI entry point
- `commands.py` - CLI commands
- `tui.py` - Text user interface
- `gui_launcher.py` - GUI launcher
- `entry.py` - Entry point
- `settings.py` - CLI settings
- `shell_config.py` - Shell configuration
- `vscode_extension.py` - VS Code extension support
- `pt_style.py` - Prompt style
- `utils.py` - CLI utilities
- `suppress_warnings.py` - Warning suppression

### `forge/critic/` - Code Critic

**Purpose:** Code review and criticism.

**Structure:**
- `base.py` - Base critic class
- `finish_critic.py` - Finish condition critic

### `forge/experiments/` - Experimental Features

**Purpose:** Experimental functionality.

**Structure:**
- `experiment_manager.py` - Experiment management

### `forge/io/` - I/O Utilities

**Purpose:** Input/output utilities.

**Structure:**
- `io.py` - I/O interface
- `json.py` - JSON utilities

### `forge/knowledge_base/` - Knowledge Base

**Purpose:** Knowledge base management.

**Structure:**
- `manager.py` - Knowledge base manager

### `forge/mcp/` - MCP Utilities

**Purpose:** Model Context Protocol utilities.

**Structure:**
- `utils.py` - MCP utilities

### `forge/microagent/` - Micro-Agents

**Purpose:** Lightweight agent implementations.

**Structure:**
- `microagent.py` - Micro-agent base
- `types.py` - Micro-agent types
- **`prompts/`** - Micro-agent prompts

### `forge/structural/` - Structural Analysis

**Purpose:** Code structure analysis.

**Structure:**
- 1 Python file

### `forge/tools/` - Tool Definitions

**Purpose:** Tool definitions and utilities.

**Structure:**
- 1 Python file

## Summary Statistics

**Total Codebase Structure:**
- **704 Python files** in backend (excluding tests)
- **983 frontend files** (584 TSX, 398 TS)
- **144,110 lines of production backend code** (Python)
- **101,417 lines of production frontend code** (TypeScript/TSX)
- **245,527 total lines of production code**
- **8,100 backend functions/methods** (average complexity: 3.06)
- **Frontend average complexity: 2.21**
- **32 route files** (API endpoints)
- **14 middleware components**
- **24 controller services**
- **5 agent types** (CodeAct, Browsing, ReadOnly, LOC, VisualBrowsing)
- **30+ LLM providers** supported
- **200+ models** available
- **4 runtime types** (Docker, Kubernetes, Local, Remote)
- **3 storage backends** (Local, S3, Google Cloud)
- **3 Git integrations** (GitHub, GitLab, Bitbucket)

**Architecture Highlights:**
- Event-driven architecture with typed event contracts
- Multi-layer caching (L1 in-memory + L2 Redis)
- Comprehensive middleware stack (14 components)
- Production-grade monitoring (30+ metrics, 3 Grafana dashboards)
- Security-first design (10 security layers)
- Extensible plugin system (runtime plugins, agent tools)
- Multi-agent orchestration (MetaSOP framework)
- Prompt optimization system (A/B testing, evolution)

