## Service API Design for Event and Runtime Services

This document captures the first-class service contracts that were carved out of the
monolithic orchestrator. Two independent services are introduced:

- `forge-event-service`: owns session lifecycle and event stream pub/sub.
- `forge-runtime-service`: manages runtime sandboxes and exposes step execution APIs.

### Architecture

The services follow a **server-to-server** architecture:

```
┌─────────┐          ┌──────────┐          ┌──────────────────┐
│ Browser │ <──WS──> │ Monolith │ <──gRPC─>│ Event/Runtime    │
│         │ (HTTP/1.1│ (FastAPI)│ (HTTP/2) │ Services         │
│         │   REST)  │          │          │                  │
└─────────┘          └──────────┘          └──────────────────┘
```

**Browser Communication:**
- Browsers connect to the FastAPI monolith via **WebSocket (Socket.IO)** or **HTTP/1.1 REST**.
- Browsers **never directly call gRPC**—they use the monolith as a gateway.
- WebSocket upgrades from HTTP/1.1 (or uses HTTP/2 if available), but this is handled automatically by the browser and server.

**Server-to-Server Communication:**
- The monolith communicates with event/runtime services via **gRPC over HTTP/2**.
- This is **server-to-server only**, so HTTP/2 support is guaranteed (all modern server stacks support it).
- gRPC's HTTP/2 usage is safe here because:
  - All gRPC server libraries (Python, Go, etc.) support HTTP/2.
  - All modern load balancers (Envoy, nginx, Kubernetes) support HTTP/2.
  - No browser compatibility concerns (browsers don't call gRPC directly).

### Transport

Both services expose gRPC endpoints (see `forge/services/protos/*.proto`). Payloads are
kept JSON-compatible so that existing Pydantic models can be re-used when bridging between
the gRPC layer and internal adapters. The services emit/consume structured events via the
existing event bus (Kafka/Redis Streams, depending on deployment).

**HTTP/2 Considerations:**
- gRPC uses HTTP/2, which is **standard for server-to-server** communication.
- Modern gRPC libraries handle HTTP/2 negotiation automatically.
- No browser compatibility concerns because browsers use WebSocket/REST to talk to the monolith.
- If browser clients ever need direct service access, we'd use **gRPC-Web** (HTTP/1.1 proxy) or a **REST gateway**.

### Event Service Contract

`event_service.proto` defines the following RPCs:

| RPC | Description |
| --- | --- |
| `StartSession` | Creates a session and initialises an `EventStream`. Returns `SessionInfo`. |
| `PublishEvent` | Accepts a single `EventEnvelope` (JSON payload) and enqueues it via `EventStream.add_event`. |
| `Subscribe` | Server streaming RPC that pushes `EventEnvelope` updates for the session. |
| `Replay` | Server streaming RPC returning `ReplayChunk` pages to reconstruct historical events. |

`EventEnvelope.payload` stores the canonical `event_to_dict` JSON for compatibility with
`forge.events.serialization` helpers.

### Runtime Service Contract

`runtime_service.proto` exposes runtime-oriented RPCs:

| RPC | Description |
| --- | --- |
| `CreateRuntime` | Creates/attaches to a runtime sandbox. Returns `RuntimeHandle`. |
| `RunStep` | Bidirectional stream that accepts `RunStepRequest` frames and emits `StepUpdate` notifications. |
| `CloseRuntime` | Tears down the runtime sandbox. |

`RunStepRequest.step` mirrors a conversation step. `StepUpdate` frames provide progress (`progress`),
result (`result`), or failure (`error`) notifications with lightweight metadata.

### Python Service Stubs

- `forge/services/event_service/service.py`: Implements `EventServiceServer` using
  `EventStream`. Subscription results are surfaced via async generators, and replay utilises
  `EventStore.search_events`.
- `forge/services/runtime_service/service.py`: Implements `RuntimeServiceServer` with
  `RuntimeOrchestrator` plus modularised adapters (`RuntimeAdapter`,
  `TemplateToolkit`, `ProfileManager`, etc.). Runtime state is tracked per `runtime_id`.

These stubs can be wrapped with generated gRPC servants (e.g. using `grpc.aio`), ensuring
the service boundary remains thin and testable.

### Adapter Layer

The `forge/services/adapters/` package provides adapter classes that bridge service contracts
with monolith implementations:

- `EventServiceAdapter`: Wraps `EventServiceServer` for in-process use or future gRPC integration.
  Provides methods like `start_session()`, `get_event_stream()`, and `publish_event()`.
- `RuntimeServiceAdapter`: Wraps `RuntimeServiceServer` for in-process use or future gRPC integration.
  Provides methods like `create_runtime()`, `close_runtime()`, and `run_step()`.

These adapters enable a gradual migration path:
1. **In-process mode** (current): Direct access to `EventStream` and `RuntimeOrchestrator`.
2. **gRPC mode** (future): Network-based service calls with automatic serialization.

### Proto Compilation

Protocol Buffer definitions are compiled to Python gRPC stubs using:

```bash
make compile-protos
# or
python scripts/compile_protos.py
```

This generates Python service stubs and message classes in `forge/services/generated/`.

### Contract Tests

Contract tests in `tests/unit/services/` verify:
- Adapter compatibility with service contracts
- In-process mode behavior matches expected service behavior
- gRPC mode raises appropriate `NotImplementedError` until implemented

### gRPC Rollout Plan

**Objective:** Transition the monolith-to-service communication path from in-process adapters to networked gRPC while preserving observability and rollback safety.

**Phase 0 — Prerequisites (Current):**
- ✅ Proto contracts, adapters, and in-process servers in place.
- ✅ `FORGE_*_SERVICE_GRPC` feature flags allow runtime selection.
- ✅ Contract/unit tests cover adapter behavior.

**Phase 1 — Client Implementation:**
- Generate Python gRPC client stubs (`grpc.aio`) alongside servers via `scripts/compile_protos.py`.
- Extend `EventServiceAdapter` / `RuntimeServiceAdapter` with gRPC client branches guarded by feature flags.
- Add connection management (channel pool, timeouts, keepalive, TLS hooks) and metadata propagation (trace IDs, auth headers).
- Instrument interceptors for logging/metrics to keep parity with in-process telemetry.

**Phase 2 — Local & Integration Validation:**
- Add adapter integration tests that stand up ephemeral gRPC servers (loopback) to exercise client paths.
- Extend smoke test (`backend/scripts/test_dispatch.py`) to run once in gRPC mode.
- Verify load-shedding behavior: simulate server outages, ensure adapters fall back or surface clear errors.
- Measure latency/throughput baselines with `pytest-benchmark` or k6 pointing at loopback servers.

**Phase 3 — Staged Deployment:**
- Ship configurable endpoints via env vars (`FORGE_*_SERVICE_ENDPOINT`).
- Enable gRPC mode in non-production environments; monitor event volumes, error rates, and trace completeness.
- Introduce per-request fallback: on gRPC failure, optionally retry via in-process path (tunable).
- Collect SLO metrics (latency, error, saturation) and update dashboards/alerts.

**Phase 4 — Production Rollout:**
- Flip feature flags progressively (canary → partial traffic → full).
- Document runbooks for failover (toggle flag, restart pods, reroute via Service Mesh).
- Conduct chaos drills: sever service connectivity, validate backpressure and recovery.
- After sustained stability, remove in-process code paths or keep as emergency fallback depending on operational comfort.

### Integration & Coverage Checklist

- **Unit:** Existing contract tests plus new gRPC client path tests for adapters (event publish, subscribe, runtime lifecycle, step execution).
- **Integration:** Loopback gRPC servers in CI + smoke test in both modes.
- **End-to-End:** API/UI conversational flow exercised in staging with gRPC enabled; verify event delivery, telemetry, and run completion.
- **Load/Resilience:** Synthetic load, forced disconnects, slow consumer scenarios.
- **Security:** mTLS or token propagation checked via interceptors; ensure secrets rotation and cert reload strategies documented.

### Next Steps

1. ✅ Generate Python/TypeScript gRPC stubs from the `.proto` definitions (proto compilation script added)
2. ✅ Create adapter layer for in-process and gRPC service integration (adapters created)
3. ✅ Add contract tests for service API compatibility (contract tests added)
4. Wire the stubs into deployment manifests (Kubernetes / Consul) and register service
   discovery endpoints
5. Extend the adapters with authentication + tracing interceptors so that request metadata
   (user, trace ID) is captured consistently across services (Phase 1)
6. Implement gRPC client stubs in adapters to enable network-based service calls (Phase 1)
7. Build integration coverage (Phase 2) and plan staged rollout (Phases 3–4)
