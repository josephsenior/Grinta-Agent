# Agent Controller Modernization & Event Pipeline Hardening

## Goals

- **Shrink and modularize `AgentController`** so lifecycle, iteration control, tool execution, safety validation, and telemetry are expressed as composable services instead of one 1,700+ line class.
- **Decouple event persistence from delivery** to prevent disk or store latency from blocking the agent/action loop.
- **Institutionalize stress testing** that simulates burst traffic, degraded storage, and recovery edge cases to guard against regressions in the new architecture.

## Current Pain Points (pre-2025 refactor)

1. **God-class controller**
   - Direct imports and attribute access from half a dozen services make responsibilities blurry.
   - Tight coupling prevents granular unit tests; most scenarios require spinning up the full controller.
   - New features routinely “leak” into the controller because there is no formal boundary or interface.
2. **Synchronous persistence hot path**
   - `EventStream.add_event` serializes and writes to disk while holding the queue lock.
   - Slow disks or large payloads stall both producer and consumer sides, defeating the async queue design.
   - Secret masking is incomplete (no list traversal) and O(n·m) for every string field.
3. **Lack of regression-proof stress coverage**
   - There is no automated way to confirm behavior when persistence slows down or when agents emit high-frequency actions.
   - Stuck detection, retries, and replay handling are not exercised under realistic load patterns.

## Target Architecture

- **Controller Composition Root**
  - `AgentController` becomes a thin coordinator that wires a well-defined set of domain services.
  - Each service consumes a constrained `ControllerContext` (state accessors, event emitters, budget mutators) instead of reaching into controller attributes.
  - Services expose explicit interfaces (e.g., `IterationManager.apply(ctx, metadata) -> None`) with unit coverage.
- **Event Pipeline Layers**
  - Event ingestion path assigns IDs, performs lightweight validation/masking, and enqueues immediately.
  - A dedicated async writer (or persistence service) drains a durability queue and handles JSON serialization + file-store writes with retry/backpressure policies.
  - Secret sanitization walks arbitrary JSON-compatible structures and uses precompiled patterns.
- **Stress & Reliability Suite**
  - New integration harness under `tests/stress/` (or `tests/integration/`) that can:
    - Emit thousands of events/second while mocking slow storage to ensure enqueue latency stays bounded.
    - Simulate agent loops with dynamic iteration adjustments, retries, and stuck detection triggers.
    - Assert metrics/backpressure counters behave as expected under load.

## Status & Incremental Plan (2025-11)

1. **Planning & Context APIs** ✅
   - `ControllerContext` plus helper adapters now gate all controller mutations.
2. **Service Extraction Waves** ✅
   - Iteration/budget control, tool orchestration, safety confirmation, pending-action tracking, and telemetry are isolated modules under `forge/controller/services`.
   - Guardrails (iteration + per-step), prerequisite checks, and autonomy gates plug into the same surface.
3. **Event Pipeline & Persistence** ✅
   - `EventStream` enqueues before writing; `DurableEventWriter` handles disk persistence.
   - Secret sanitizer walks arbitrary containers with precompiled regexes.
4. **Delegate Runtime Layer** ✅
   - `DelegateRunContext` codifies shared resources.
   - `DelegateRuntimeProvider` provisions forked runtimes via the RuntimeOrchestrator and bridges events back to the parent controller.
5. **Telemetry & Stress Harness** ✅
   - Prometheus exposes guardrail, replay, and runtime metrics; stress suites live under `tests/stress/` and `tests/unit/runtime/test_watchdog.py`.

### Remaining Nice-to-haves
- Auto-scaling warm pools driven by the new `forge_runtime_scaling_signals_*` counters.
- Delegate fork pools (copy-on-write snapshots) for even faster clones.
- Additional stress scenarios that combine recovery + guardrails under heavy load.

## Open Questions & Decisions Needed

- **Service Boundary Depth:** Should services be pure functions receiving context objects, or lightweight classes retaining their own state? (Recommendation: classes with explicit `start/stop` hooks for lifecycle alignment.)
- **Persistence Guarantees:** Accept eventual persistence (events may sit in queue briefly) or require synchronous durability acknowledgement before informing upstream? (Recommendation: enqueue-first with configurable sync barrier for high-compliance deployments.)
- **Stress Suite Placement:** Keep inside core test runner or separate `pytest -m stress` target? (Recommendation: mark as `@pytest.mark.stress` and run selectively.)

## Next Actions

1. Implement `ControllerContext` dataclass + base protocols for services.
2. Extract telemetry/tool pipeline handling as the pilot slice and wire through dependency injection.
3. Prototype the `DurableEventWriter`, gated behind a feature flag, and benchmark under synthetic load.
4. Stand up initial stress test that reproduces current blocking behavior to prove the fix.

## Service Boundary Summary (2025-11-15)

| Service | Responsibilities | Key Inputs | Key Outputs/Side Effects |
|---------|------------------|------------|---------------------------|
| `LifecycleService` | Initialize controller identity, event stream subscriptions, state tracker wiring, replay context | Config, file store, event stream | Controller core attrs, `state_tracker`, replay manager |
| `IterationGuardService` | Run control flags, enforce iteration/budget ceilings, graceful shutdown | Controller state flags, metrics | Updates agent state, emits halt events |
| `StepGuardService` | Per-step circuit breaker enforcement, stuck detection hooks | `CircuitBreakerService`, `StuckDetectionService` | Raises guardrail errors, records telemetry |
| `StepPrerequisiteService` | Ensure controller can step (RUNNING, no pending action awaiting observation) | Controller state, PendingActionService | Blocks steps until prerequisites satisfied |
| `BudgetGuardService` | Sync budget control flags with LLM usage metrics before each step | Conversation stats, state tracker | Updates budget flags, emits overrun telemetry |
| `ActionExecutionService` | Fetch actions via `ConfirmationService`, coordinate tool pipeline plan/execute, handle context-window/API errors | Tool pipeline, `ControllerContext` | Runs tool plans, registers action contexts |
| `PendingActionService` | Track pending actions, emit timeout information for guards/telemetry | Event stream, controller state | Provides pending info to guard services |
| `ConfirmationService` | Replay/live action sourcing, confirmation policy, pending-action transitions | Replay manager, autonomy settings | Logs action telemetry, transitions agent state |
| `ObservationService` | Log observations, run pipeline observe stage, prepare action metrics | Observations, tool pipeline, controller metrics | Ensures contexts cleaned up, metrics attached |
| `DelegateService` | Delegate spawn/teardown, task priming, completion observations | `AgentDelegateAction`, `DelegateRunContext` | Emits `AgentDelegateObservation`, restores parent iteration metrics |
| `DelegateRuntimeProvider` | Acquire/release delegate runtimes via orchestrator, mirror events back to parent stream | Runtime pool/orchestrator, repo/env context | Provides `DelegateRuntimeHandle` to `DelegateService` |
| `RecoveryService` | Exception classification, retry orchestration, status callbacks, rate-limit handling | Exceptions, Retry/CircuitBreaker services | Schedules retries, emits `controller_recovery` events |
| `TelemetryService` | Tool middleware stack construction, blocked-action telemetry | Controller config | Emits pipeline- and action-level metrics |
| `SafetyService` | Security analyzer invocation, confirmation gating, pending-action resolution | Actions, analyzer, autonomy controller | Mutates action confirmation state, logs risk decisions |

Each service receives a `ControllerContext`, keeping direct access to controller internals centralized and auditable. New features should be added by composing or extending these services (or helpers like `DelegateRuntimeProvider`) instead of modifying `AgentController` directly.

## Config Safety Notes (2025-11-14)

- `AgentConfig` now rejects unknown fields in both the base section and `agent.*` overrides. Invalid keys or malformed values raise a `ValueError` during startup instead of being silently ignored, preventing misconfigured agents from loading behind the scenes. Configs should declare `schema_version = "2025-11-15"`; mismatches are logged and exported via Prometheus (`forge_agent_config_*` metrics) so we can spot outdated bundles quickly.


