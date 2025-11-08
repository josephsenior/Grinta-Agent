# Forge Architecture

## Overview

Forge is a production-grade AI coding agent system built on a 5-layer architecture, currently optimized for the CodeAct agent (beta launch focus).

### Code Quality
- **125,186 total lines** (81,934 source lines of code)
- **5,931 functions/methods**
- **Average complexity: 3.13** (A-rated)
- **0% high-complexity functions** (industry-leading)
- See [CODE_QUALITY.md](CODE_QUALITY.md) for detailed metrics

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
│  Layer 2: FastAPI Server (73 Route Files)               │
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
│  • Action execution server                              │
│  • Docker-based isolation                               │
│  • File operations (read, write, edit)                  │
│  • Browser automation                                   │
└─────────────────────────────────────────────────────────┘
```

## Data Flow: User Request → Agent Response

```
User sends message via WebSocket
   ↓
Message received by server (Forge/server/listen.py)
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
WebSocket sends update to frontend
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
- `Forge/core/config/api_key_manager.py` - Secure key management, provider detection
- `Forge/core/config/provider_config.py` - 30 provider configurations with validation rules
- `Forge/llm/model_features.py` - Feature detection (function calling, caching, vision)
- `Forge/llm/llm.py` - Main LLM class with retry logic, cost tracking

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
1. **Risk Assessment** - AI-powered analysis of commands (`Forge/security/analyzer.py`)
2. **Sandbox Execution** - Docker container isolation
3. **Input Validation** - Command injection prevention
4. **Rate Limiting** - Prevent abuse (1000 req/hour)
5. **Cost Quotas** - Budget protection ($1/day free tier)

### 5. Monitoring System (Production-Grade)

**Grafana Dashboards (3):**

| Dashboard | Purpose | Key Metrics |
|-----------|---------|-------------|
| llm-performance.json | LLM monitoring | Latency (p50/p90/p95), tokens, costs |
| system-metrics.json | System health | CPU, memory, active conversations |
| error-tracking.json | Error monitoring | Error rates, failure patterns |

**Prometheus Metrics (30+):**

```
# Sample metrics from forge/metasop/metrics.py

metasop_steps_executed          # Total steps executed
metasop_steps_failed            # Failed steps
metasop_total_tokens            # Token consumption
metasop_model_total_tokens{model="claude-4"}  # Per-model tokens
metasop_step_duration_ms_p95    # p95 latency
metasop_cache_hits              # Cache efficiency
metasop_retry_attempts          # Retry patterns
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

### 6. HTTP Caching (Already Implemented)

**File:** `Forge/server/middleware/compression.py`

**Features:**
- ETag generation for cache validation
- Cache-Control headers (static assets: long TTL, APIs: configurable)
- Compression (gzip/brotli)
- Conditional requests (304 Not Modified)

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
- **LLM Integration:** LiteLLM (200+ models)
- **Database:** SQLAlchemy (async)
- **WebSocket:** FastAPI WebSocket
- **Containerization:** Docker
- **Monitoring:** Prometheus + Grafana
- **Logging:** Structured JSON logging

### Frontend
- **Framework:** React 18 with TypeScript
- **State:** Redux Toolkit + React Query
- **Styling:** Tailwind CSS
- **Real-time:** WebSocket client
- **Icons:** Lucide React
- **Animations:** Framer Motion
- **Build:** Vite

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

**Current (Beta):**
- Single server instance
- SQLite or PostgreSQL
- In-memory caching
- Handles: 100-1000 users

**Future Scaling:**
- Horizontal scaling (multiple server instances)
- Redis for distributed caching
- Database read replicas
- Load balancer
- Handles: 10,000+ users

## References

- [Getting Started](./GETTING_STARTED.md) - Quick start guide
- [API Reference](./API_REFERENCE.md) - Complete API documentation
- [Monitoring Guide](./MONITORING.md) - Monitoring and observability
- [Troubleshooting](./TROUBLESHOOTING.md) - Common issues
- [Beta Launch Strategy](./beta-launch-strategy.md) - Beta configuration

## Component Details

For deep dives into specific components:
- **LLM System:** See `Forge/llm/README.md`
- **CodeAct Agent:** See `Forge/agenthub/codeact_agent/README.md`
- **Security:** See `Forge/security/README.md`
- **Frontend:** See `frontend/README.md`

