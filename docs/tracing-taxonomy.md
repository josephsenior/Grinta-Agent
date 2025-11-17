# Tracing Taxonomy and Naming

This document defines the span hierarchy, naming, and attributes for Forge tracing. It follows OpenTelemetry semantic conventions, adds AI/LLM attributes, and supports reliable log correlation and privacy.

## Principles
- Prefer semantic conventions: http, db, rpc, exception, cloud, process, thread.
- Use stable names; avoid raw IDs in span names. Put PII/secrets only in attributes that are safe and redacted.
- Keep hierarchy shallow but expressive; use span links for async hops.
- Consistent resource attributes to group data across services and environments.

## Resource Attributes
- service.name: "forge-api"
- service.namespace: "forge"
- service.version: app `__version__`
- deployment.environment: from `FORGE_ENV|ENV|PYTHON_ENV|NODE_ENV` (lowercase)
- service.instance.id: hostname or pod name

## Span Hierarchy (typical request)
1) SERVER span: HTTP request
   - Name: "HTTP {method} {http.route}"
   - Kind: SERVER
   - Attrs: http.method, http.route, http.target, http.url, http.request.body.size, http.response.body.size, client.address, user_agent.original

2) Orchestration span: conversation run
   - Name: "conversation.run"
   - Kind: INTERNAL
   - Attrs: conversation.id, session.id, run.id, goal.id, step.count

3) Agent step spans (repeat)
   - Name: "agent.step"
   - Kind: INTERNAL
   - Attrs: agent.name, step.id, action.type, plan.id

4) Tool/IO spans (children of step or run)
   - LLM call: see below
   - Redis ops: cache, rate limit, quota
   - HTTP client calls: external APIs
   - MCP requests: to MCP servers/tools

## Naming Conventions
- Use dot-separated verbs: "conversation.run", "agent.step", "tool.exec", "llm.call", "cache.get", "cache.set", "rate_limit.check", "quota.apply", "mcp.request".
- For HTTP CLIENT spans, keep standard HTTP naming: "HTTP POST https://api.vendor.tld/path" or normalized vendor host.

## Attributes by Span Type

### HTTP SERVER (existing)
- http.method, http.route, http.target, http.url, http.status_code
- forge.request_id (if available)
- net.sock.peer.port, client.address, user_agent.original (optional)

### Conversation Orchestration
- conversation.id, session.id, run.id
- user.id (hash or internal surrogate; avoid PII)
- goal.id, plan.id
- duration.ms (optional duplicate for convenience)

### Agent Step
- agent.name, agent.type
- step.id, step.index
- action.type (e.g., "FileEdit", "Search", "RunTests")
- inputs.size_bytes, outputs.size_bytes (if measurable)

### LLM Call (CLIENT)
- llm.provider (openai|anthropic|google|azure|ollama|…), llm.model
- llm.temperature, llm.top_p, llm.max_tokens (if set)
- llm.input_tokens, llm.output_tokens, llm.total_tokens
- llm.cost.usd, llm.cache_hit (true|false|unknown)
- server.address (api host), server.port (if known)
- http.status_code (from vendor reply if HTTP-based)

### Tool Exec
- tool.name, tool.kind (mcp|http|filesystem|git|custom)
- tool.input_size_bytes, tool.output_size_bytes
- tool.status (ok|error|timeout|rate_limited)
- retries.attempt, retries.backoff_ms (if applicable)

### MCP Request (CLIENT)
- mcp.server.name, mcp.method, mcp.resource
- http.status_code or mcp.status (normalized)
- input.size_bytes, output.size_bytes

### Redis / Cache
- db.system="redis", db.operation (GET|SET|EVAL|INCR|TTL|PFADD etc.)
- db.redis.database_index, net.peer.name, net.peer.port
- cache.hit (true|false), cache.key (hashed or redacted), cache.ttl_ms (if known)

### HTTP CLIENT (generic external)
- http.method, url.full or server.address + url.path
- http.status_code, network.error.type (on failure)
- retries.attempt, retries.backoff_ms (events or attrs)

## Events (add to spans when useful)
- "retry": {attempt, backoff_ms, reason}
- "rate_limited": {limit_name, window_s}
- "validation_error": {field, reason}
- "stream_chunk": {index, size_bytes} (be selective to avoid high cardinality)

## Status and Errors
- On failure, record exception and set status=ERROR with a brief, non-sensitive description.
- Avoid including secrets or raw payloads in events or attributes.

## Context Propagation
- Use W3C tracecontext (`traceparent`, `tracestate`) over HTTP and WS when feasible.
- For background tasks and WebSocket flows, use span links to connect back to the originating HTTP request.
- Bridge Forge thread-local `trace_id` to OpenTelemetry context for unified log correlation (implementation item).

## Sampling Strategy (initial)
- Head sampling default: 5% for generic requests.
- Always sample errors and 100% for conversation orchestration (`/api/conversation*`, metasop flows).
- Allow per-route overrides via env (e.g., `OTEL_SAMPLE_ROUTES=/api/conversation:1.0;/api/files:0.1`).

## Privacy and Redaction
- Never record prompt text or file contents in span attributes.
- Only log sizes, token counts, and metadata needed for ops.
- Redact or hash keys (e.g., cache.key_hash) instead of raw values.

## Example Tree

HTTP GET /api/conversations/{id}
  conversation.run
    agent.step (action=Plan)
      llm.call (provider=anthropic, model=claude-3-5)
    agent.step (action=FileEdit)
      tool.exec (tool=filesystem.write)
      cache.get (db=redis)
    agent.step (action=RunTests)
      HTTP POST https://ci.internal/run

## Minimum Viable Implementation Order
1) Add log correlation (trace_id/span_id) to logs from current span.
2) Instrument LLM calls (litellm wrappers) with tokens/cost.
3) Instrument Redis (rate limit, quota, cache) operations.
4) Instrument MCP/tool exec and external HTTP calls.
5) Instrument conversation.run and agent.step around orchestrator.
6) Add sampling controls and per-route overrides.

## Configuration Flags
- `OTEL_ENABLED`: master switch enabling basic HTTP spans and log correlation defaults.
- `OTEL_LOG_CORRELATION`: inject `trace_id` and `span_id` into logs (defaults to `OTEL_ENABLED`).
- `OTEL_INSTRUMENT_LLM`: enable `llm.call` CLIENT spans (defaults to `OTEL_ENABLED`).
- `OTEL_INSTRUMENT_REDIS`: enable Redis CLIENT spans for rate limiting and cost quota (defaults to `OTEL_ENABLED`).
- `OTEL_INSTRUMENT_ORCHESTRATION`: create a `conversation.run` INTERNAL span from the orchestrator root (optional advanced; defaults to off unless `OTEL_ENABLED=true`).
- `OTEL_INSTRUMENT_MCP`: enable MCP tool execution CLIENT spans (defaults to `OTEL_ENABLED`).
 - `OTEL_SAMPLE_HTTP`: head sampling probability (0.0–1.0) for HTTP SERVER spans (default falls back to `OTEL_SAMPLE_DEFAULT` or 1.0).
 - `OTEL_SAMPLE_LLM`: sampling probability for `llm.call` spans.
 - `OTEL_SAMPLE_REDIS`: sampling probability for Redis spans (`rate_limit.check`, `quota.check`, `quota.record_cost`).
 - `OTEL_SAMPLE_MCP`: sampling probability for `mcp.request` spans.
 - `OTEL_SAMPLE_DEFAULT`: fallback sampling rate used when a type-specific variable is unset.
 - `OTEL_SAMPLE_ROUTES`: semicolon-delimited overrides for HTTP SERVER spans. Format: `/api/conversations*:1.0;/api/files:0.2;/api/monitoring*:1.0`. Use `*` suffix for prefix match; exact paths without `*` require full equality.
 - `OTEL_SAMPLE_ROUTES_REGEX`: semicolon-delimited regex overrides for HTTP SERVER spans. Format: `^/api/(conversations|files)(/.*)?$:1.0;^/private/.*:0.0`. Regex rules are evaluated left-to-right and take precedence over `OTEL_SAMPLE_ROUTES`.

Sampling evaluation happens BEFORE span creation (head sampling) to avoid overhead. Each sampler env var is parsed as a float; invalid values fall back to 1.0. Values are clamped to `[0.0,1.0]`.

Examples:
```
# Sample 5% of generic HTTP traffic, but keep full fidelity for LLM & MCP
OTEL_SAMPLE_DEFAULT=1.0
OTEL_SAMPLE_HTTP=0.05
OTEL_SAMPLE_LLM=1.0
OTEL_SAMPLE_MCP=1.0
OTEL_SAMPLE_REDIS=0.25   # moderate sampling for noisy Redis ops

# Disable all tracing except critical orchestration (set orchestrator flag separately)
OTEL_ENABLED=true
OTEL_SAMPLE_DEFAULT=0.0
OTEL_SAMPLE_HTTP=0.0
OTEL_SAMPLE_LLM=0.0
OTEL_SAMPLE_REDIS=0.0
OTEL_SAMPLE_MCP=0.0
```

Operational Guidance:
- Start with `HTTP=0.05, REDIS=0.2, LLM=1.0, MCP=1.0` in production for good cost/visibility balance.
- Temporarily raise `OTEL_SAMPLE_REDIS` to 1.0 when debugging throttle behavior.
- Keep LLM at 100% until confident in cost distribution; then consider 0.5–0.8 if volume is extreme.
- MCP tool creation calls are usually low QPS; keep at 1.0.
 - Use `OTEL_SAMPLE_ROUTES` to force 100% sampling for critical flows (e.g., `/api/conversations*`) while keeping baseline HTTP sampling low.
 - Prefer `OTEL_SAMPLE_ROUTES_REGEX` when you need complex patterns or groupings; it overrides simple route rules when both match.

## New Span Names and Attributes
- `HTTP {method} {route}` (SERVER): `http.*`, `forge.request_id`, `forge.trace_id`.
- `conversation.run` (INTERNAL): `conversation.id`, `conversation.run_id`, `forge.trace_id`.
- `llm.call` (CLIENT): `llm.provider`, `llm.model`, `llm.temperature`, `llm.top_p`, `llm.max_tokens`, `llm.streaming`, `llm.latency_ms`, `llm.input_tokens`, `llm.output_tokens`, `llm.total_tokens`, `llm.cache_hit_tokens`, `llm.cache_write_tokens`, `llm.cost.usd`, `forge.trace_id`.
- `rate_limit.check` (CLIENT, Redis): `db.system=redis`, `ratelimit.key`, `ratelimit.hour.count`, `ratelimit.hour.limit`, `ratelimit.burst.count`, `ratelimit.burst.limit`, `ratelimit.allowed`, `forge.trace_id`.
- `quota.check` (CLIENT, Redis): `db.system=redis`, `quota.key`, `quota.plan`, `quota.daily.cost`, `quota.daily.limit`, `quota.monthly.cost`, `quota.monthly.limit`, `quota.allowed`, `forge.trace_id`.
- `quota.record_cost` (CLIENT, Redis): `db.system=redis`, `quota.key`, `quota.cost.usd`, `forge.trace_id`.
- `mcp.request` (CLIENT): `tool.name`, `tool.kind=mcp`, `mcp.server.name`, `mcp.method`, `mcp.resource`, `conversation.id`, `forge.trace_id`.

Note: All spans avoid storing prompt text or payloads; only aggregate metrics and identifiers are captured.
