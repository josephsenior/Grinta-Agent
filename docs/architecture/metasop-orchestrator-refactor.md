# MetaSOP Orchestrator Modularization Map

## Current Responsibility Buckets

- **Bootstrap & Configuration**  
  Handles settings loading, profile/schema hydration, tool discovery, and runtime feature flags.
- **Execution Lifecycle**  
  Orchestrates step scheduling, retries, QA loops, ACE/parallel engines, and plan progression.
- **Cache & Memory Management**  
  Controls step cache, context hashing, memory store binding, and retrieval strategies.
- **Event & Telemetry Pipeline**  
  Emits runtime events, binds trace IDs, manages logging bridges, metrics, and efficiency reporting.
- **Failure Analysis & Remediation**  
  Classifies errors, builds remediation plans, corrective hints, and integrates taxonomy feedback.
- **Artifact & Verification Handling**  
  Normalizes artifacts, QA summaries, outcome verification, and diff fingerprints.
- **Integrations & External Systems**  
  Interfaces with predictive planners, collaborative streaming, selective tests, and role profiles.

## Target Module Layout (First Pass)

- `forge.metasop.core.bootstrap` – settings, template/model discovery, tool validation.
- `forge.metasop.core.execution` – primary run loop, step queueing, retry policy enforcement.
- `forge.metasop.core.memory` – cache coordination, memory index/store adapters.
- `forge.metasop.telemetry` – logging/tracing setup, event emission helpers, metrics utilities.
- `forge.metasop.core.failure_handling` – diagnosis, remediation selection, hint generation.
- `forge.metasop.core.artifacts` – artifact normalization, diff/verification helpers.
- `forge.metasop.core.integrations` – wrappers for ACE, parallel execution, predictive engines.

## Incremental Extraction Plan

1. **Telemetry Slice (low coupling)**
   - Move `_setup_logging_and_tracing`, `_emit_event` helpers, and metrics utilities into `forge.metasop.telemetry`.
   - Provide a small facade class used by orchestrator; add unit tests for event enrichment.
2. **Failure Handling Utilities**
   - Extract remediation, taxonomy, and hint builders into `core.failure_handling`.
3. **Artifact & Verification Helpers**
   - Isolate verification and diff helpers to reduce noise in execution loop.
4. **Execution Core Decomposition**
   - Split run loop from initialization; orchestrator becomes a thin composition root.
5. **Memory & Cache Module**
   - Extract memory binding/retrieval logic alongside cache strategy adapters.
6. **Integration Facades**
   - Wrap optional engines (ACE, parallel, predictive, streaming) with explicit interfaces.

Each step should land with dedicated unit coverage and no functional regressions; update import paths only after modules are in place. Track progress in change log and wire new modules via dependency injection so the orchestrator file continues to shrink safely.


## Runtime Isolation Service (Step 4)

- **Component:** `forge.runtime.runtime_manager`
- **Purpose:** Provide a first-class runtime-management surface that decouples sandbox lifecycle from the MetaSOP orchestrator.
- **Responsibilities:**
  - Coordinate warm pools per runtime kind (local, Docker, remote) so the API/WebSocket tier can scale independently of sandbox provisioning.
  - Register and deregister active sessions with lightweight metadata (ports, container names, runtime IDs) to simplify failure isolation and future autoscaling hooks.
  - Publish metrics snapshots that power the Prometheus gauges `forge_runtime_warm_pool_total` and `forge_runtime_running_sessions_total`.
- **Integrations:**
  - `LocalRuntime`, `DockerRuntime`, and `RemoteRuntime` now delegate pooling and session bookkeeping to the manager instead of their own module-level globals.
  - The monitoring stack consumes the manager snapshot to expose pool health in Grafana and to drive alerts when warm capacity is exhausted or sessions leak.

Extracting this slice keeps sandbox lifecycle concerns out of the orchestrator file, enabling richer runtime policies (autoscaling, sandbox health gates, remote orchestration) without re-entangling execution logic.


