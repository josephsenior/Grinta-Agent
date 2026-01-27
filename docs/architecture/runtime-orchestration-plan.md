# Runtime Orchestration & Delegate Lifecycle Modernization

## Goals

1. **Isolate runtime provisioning** – sandbox setup, repository mounting, and MCP wiring should be handled by a dedicated `RuntimeOrchestrator` instead of being scattered across `AgentController`, `LifecycleService`, and ad-hoc helpers.
2. **Introduce session/worker pooling** – allow warm sandbox reuse and delegate-safe handoffs without reinitializing an entire runtime per task.
3. **Standardize delegate lifecycle** – now that `DelegateService` manages controller-side logic, ensure runtime resources (ports, repo mounts, caches) are created and reclaimed via the same orchestrator to prevent leaks.
4. **Provide observability hooks** – emit structured telemetry for sandbox start/stop, pool health, and delegate usage to power dashboards/alerts.

## Current Pain Points

- Runtime initialization logic lives in `forge/core/setup.py`, `AgentController.start_delegate`, and multiple places under `runtime/`, making it difficult to reason about which components own sandbox state.
- Delegates and parent controllers compete for the same runtime resources because there is no explicit provisioning contract; cleanup relies on controller callbacks only.
- Warm pools exist for some runtime types, but they are hidden inside specific runtime classes (`LocalRuntime`, `DockerRuntime`). There is no shared policy (max warm count, eviction strategy).
- Observability is limited to log statements; no single place aggregates runtime lifecycle events for telemetry or alerting.

## Proposed Architecture

### 1. `RuntimeOrchestrator`

- Lives under `forge/runtime/orchestrator.py`.
- Responsibilities:
  - Accept runtime configuration (sandbox type, repo info, MCP settings).
  - Manage lifecycle hooks (`acquire`, `release`, `teardown`) and ensure they are awaited properly.
  - Attach metadata (session ID, delegate level, repo mount) for telemetry.
  - Provide a minimal interface to controllers/services (e.g., `get_runtime(session_id)`).
- Implementation outline:
  - Wrap existing `create_runtime`/`initialize_repository_for_runtime` logic.
  - Emit events to a new `RuntimeLifecycleService` (structured logs + optional events).

### 2. Session / Delegate Pool

- Backed by a `RuntimePool` abstraction with pluggable strategies:
  - `SingleUse`: current behavior.
- `WarmPool`: keep `n` sandboxes alive, keyed by runtime type + repo. Policies are configurable per runtime key (`max_size`, `ttl_seconds`) and are pushed from `ForgeConfig`.
- Delegates receive dedicated runtimes provisioned via the orchestrator; no in‑process forking of a parent runtime. Event streams are bridged back to the parent for a unified view.
- Pool stores metadata (`last_used`, `owner`) and tracks idle reclaims and capacity evictions for telemetry. Provides `checkout()` / `checkin()` to the orchestrator.

### 3. Delegate Integration

- `DelegateService` requests runtimes via `DelegateRuntimeProvider`, which acquires dedicated sandboxes from the orchestrator and bridges events back to the parent stream.
- When a delegate finishes, `DelegateRuntimeProvider` guarantees teardown and calls `RuntimeOrchestrator.release(...)` so runtimes are returned to the appropriate pool or terminated per policy.
- Parent state (repo selection, provider tokens, env) is inherited as inputs to provisioning; controller-internal state is captured via `DelegateRunContext` and attached to the delegate controller.
- `DelegateRunContext` (forge/controller/services/delegate_context.py) captures the shared resources a delegate must inherit (event stream, file store, conversation stats, iteration flag). Delegate creation validates those invariants so future isolated runtimes have an explicit contract to evolve.
- Guardrail events (`guardrail_concurrency`, `step_runtime_metrics`) are emitted by the `GuardrailService` and exposed via Prometheus metrics such as `guardrail_concurrency_total`, `guardrail_concurrency_peak`, and `guardrail_runtime_avg_ms`.

### 4. Telemetry & Alerts

- Orchestrator emits structured events (JSON) to `TelemetryService`:
  - `runtime_acquired`, `runtime_released`, `pool_exhausted`, `delegate_spawned`.
- Add counters/gauges for pool size, warm start hit rate, and delegate success/error counts.
- Runtime watchdog export includes `forge_runtime_watchdog_watched` (gauge of live sandboxes by runtime kind), `forge_runtime_pool_idle_reclaim_total` (warm entries reaped by TTL/cleanup), and `forge_runtime_pool_eviction_total` (capacity-driven evictions) so operators can distinguish “stuck sandbox” kills from proactive idle maintenance.
- Pool policies are configurable via `runtime_pool` in `config*.toml` (per-runtime `max_size` and `ttl_seconds`, plus a global `enabled` flag). `RuntimeOrchestrator` pushes those settings into `WarmRuntimePool`.
- Adaptive telemetry hooks emit `forge_runtime_scaling_signals_*` counters when the orchestrator notices idle-reclaim spikes (overprovision), warm-pool evictions (capacity exhausted), or watchdog saturation (active runtimes meet/exceed warm capacity). These signals power alerts and tuning.
- Expected metrics are documented in `docs/architecture/controller-service-directory.md`.
- Controller execution remains service-composed; guardrail concurrency and per‑step runtime telemetry surface via Prometheus without bespoke emission layers.
- Budget monitoring is handled by guard/telemetry services that aggregate LLM usage and flip halt flags when hard limits are hit; remaining steps are skipped gracefully with recovery events.

### 5. Watchdog & Lifecycle Guards

- A dedicated `RuntimeWatchdog` (`forge/runtime/watchdog.py`) tracks every sandbox checked out through the orchestrator.
- Heartbeats are derived from `EventStream` activity; lack of activity for `FORGE_RUNTIME_MAX_ACTIVE_SECONDS` (default 1h) triggers an automatic disconnect with telemetry (`forge_runtime_watchdog_terminations_*`).
- The watchdog also invokes `WarmRuntimePool.cleanup_expired()` on a fixed interval so idle warm entries are proactively reaped instead of waiting for the next acquire.
- Alerts can key off:
  - `forge_runtime_watchdog_terminations_total` (severe if >0 in prod)
  - `forge_runtime_pool_size_total` saturation
  - delegate fork counters skewed vs. parent warm hits

## Incremental Plan

1. **Abstraction Layer**
   - Create `RuntimeOrchestrator` class with current behavior (no pooling yet).
   - Update `forge/core/setup.py` and `DelegateService` to use it.
2. **Pooling Infrastructure**
   - Implement `RuntimePool` interface + `SingleUsePool` (no reuse) to keep behavior unchanged.
   - Add metrics/telemetry scaffolding.
3. **Delegate Runtime Sharing**
   - Move delegates to dedicated runtimes acquired via orchestrator. ✅ Landed via `DelegateRuntimeProvider` with event bridging and guaranteed release.
   - Update `DelegateService` to request runtimes for delegates via orchestrator. ✅ Done.
4. **Warm Pool Optimization**
   - Add `WarmPool` with per‑key policies (`max_size`, `ttl_seconds`). ✅
   - Expose configuration through `ForgeConfig` and `config*.toml`. ✅
5. **Observability**
   - Instrument orchestrator events and Prometheus metrics (pool reclaims/evictions, watchdog watched, scaling signals). ✅
6. **Documentation & Migration**
   - Update service directory + diagrams. ✅
   - Provide migration checklist for other teams (CLI, server) to adopt orchestrator APIs.

## Risks & Open Questions

- **State isolation**: ensuring delegate forks cannot mutate parent runtime state unexpectedly (particularly for file systems). Might require copy-on-write or overlay FS.
- **Security**: pooling sandboxes may retain credentials; need policy controls per tenant.
- **Backward compatibility**: CLI scripts or integrations that bypass `AgentController` will need access to orchestrator APIs.

Next steps: implement step (1) (orchestrator wrapper) and add tests around runtime acquisition/release before introducing pooling logic.

