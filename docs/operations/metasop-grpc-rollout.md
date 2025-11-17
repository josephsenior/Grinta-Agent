## MetaSOP gRPC Rollout Plan

### Overview

Promote the EventService and RuntimeService adapters to gRPC mode in a staged, observable fashion. Monoliths continue to default to in-process adapters; gRPC can be enabled per-environment via feature flags.

### Configuration Flags

- `FORGE_EVENT_SERVICE_GRPC`: `true` to enable gRPC EventService adapter.
- `FORGE_RUNTIME_SERVICE_GRPC`: `true` to enable gRPC RuntimeService adapter.
- `FORGE_EVENT_SERVICE_ENDPOINT`: host:port for EventService.
- `FORGE_RUNTIME_SERVICE_ENDPOINT`: host:port for RuntimeService.

Ensure values are supplied via Helm/Terraform for staging/canary/prod. Defaults remain `false`/in-process.

### Deployment Phases

1. **Canary**
   - Enable gRPC on a single API pod or non-prod environment.
   - Verify request latency, RPC error rates, event throughput.
   - Confirm trace IDs and client IDs appear in logs.

2. **Partial Rollout**
   - Gradually expand to ~30-50% of API replicas.
   - Continue monitoring metrics; compare with in-process baselines.

3. **Full Rollout**
   - Flip all replicas to gRPC when stable for >24h.
   - Keep feature flags available for emergency rollback.

### Observability

**Dashboards**
- Request latencies (`StartSession`, `PublishEvent`, `CreateRuntime`, `RunStep`).
- RPC error counts by status code (DeadlineExceeded, Unavailable, PermissionDenied).
- Event throughput (messages/minute). 

**Logging**
- Include `x-client-id`, `x-trace-id`, and authorization metadata in access logs.

**Alerts**
- Trigger alert if:
  - RPC error rate > 5% for 5 minutes.
  - p95 latency exceeds target thresholds (set per RPC).
  - Event backlog grows beyond acceptable watermark.

### Rollback Procedure

1. Set `FORGE_EVENT_SERVICE_GRPC=false` and `FORGE_RUNTIME_SERVICE_GRPC=false`.
2. Redeploy/restart API pods.
3. Confirm adapters reconnect in in-process mode (inspect logs).
4. Keep gRPC services running; no code changes required.

Document rollback steps in on-call runbook and ensure SREs have access.

### Pre-Rollout Checklist

- [ ] Integration tests (`pytest -m integration tests/integration/services/test_grpc_mode.py`) passing.
- [ ] Smoke test (`python scripts/smoke_metasop.py --grpc`) green in staging.
- [ ] Dashboards and alerts configured.
- [ ] TLS/mTLS (if applicable) configured for gRPC endpoints.
- [ ] Feature flag values templated in deployment configurations.

### Post-Rollout Validation

- Verify throughput/latency parity with in-process baseline.
- Run smoke test post-deployment.
- Capture trace samples to ensure metadata propagation.
- Collect feedback from on-call regarding operational noise.

### Ownership

- **Primary**: MetaSOP Orchestration Team
- **Support**: SRE (Runtime & Events)
- Escalation: #metasop-ops channel
