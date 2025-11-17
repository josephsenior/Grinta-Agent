# Future Enhancements (Observability, Security, Reliability)

This document captures prioritized, non-breaking enhancements to consider next. Each item includes rationale and a simple acceptance checklist.

## Security

- Strict CSP default in production
  - Rationale: Reduce XSS risk by default; opt-in relaxation when needed.
  - Plan: `CSP_POLICY=strict` as default when `ENV=production`; keep report-only toggles for rollout.
  - Accept when: Strict CSP applied in prod builds; docs include override guidance; dashboards show CSP report trends.

- Browser CSRF tokens for form posts (if applicable)
  - Rationale: Complement origin/referer checks with token-based protection for browser-submitted state changes.
  - Plan: Issue CSRF token cookie + header on form POST flows; validate in middleware.
  - Accept when: Token present and validated on mutating routes; compatibility mode available via env.

## Observability & Metrics

- Prometheus recording rules for latency percentiles
  - Rationale: Cheap p50/p90/p95/p99 without heavy query cost on dashboards.
  - Plan: Add recording rules for `forge_request_duration_ms_bucket` to compute percentiles; wire to dashboards.
  - Accept when: Grafana shows percentiles with <200ms panel load time using recording rules.

- Service-level indicators (SLIs) and SLOs
  - Rationale: Formalize reliability targets for availability, latency, and error rate.
  - Plan: Define SLIs using new method/status labels; add SLO panels and alert rules.
  - Accept when: SLO dashboards and alerts are active with clear runbooks.

- Route-normalized metrics (low-cardinality)
  - Rationale: Visibility per API surface without exploding label space.
  - Plan: Emit `route="/api/monitoring/health"` or named handlers; ensure bounded set.
  - Accept when: PromQL showing per-route success rate is stable and label cardinality remains low.

## WebSocket Controls

- Redis-backed global rate limiting for `/ws/live`
  - Rationale: Enforce concurrent and attempt limits across replicas; prevent abuse.
  - Plan: Mirror HTTP limiter design with Redis keys for attempts and active counts; include ban windows.
  - Accept when: Limits enforced cluster-wide; tests simulate multi-client behavior.

- Env-configurable WS limits
  - Rationale: Tune limits per environment without code changes.
  - Plan: `WS_MAX_CONCURRENT_PER_IP`, `WS_BURST_PER_MIN`, `WS_HOURLY_LIMIT` envs with sane defaults and docs.
  - Accept when: Limits change via env and reflected in logs/metrics.

## Reliability & Ops

- Enhanced readiness checks
  - Rationale: Catch degraded dependencies early.
  - Plan: Optional checks for DB, external HTTP dependencies; timeouts <1s; feature-gated via env.
  - Accept when: Readiness remains fast and accurate; compose/k8s healthchecks leverage it.

- Log rotation and retention guidance
  - Rationale: Prevent disk growth; align with ops standards.
  - Plan: Document rotation via file handler or system logrotate; sample configs.
  - Accept when: Docs provide copy-paste configs and operational notes.

## Tracing

- OpenTelemetry tracing
  - Rationale: End-to-end correlation across services and external calls.
  - Plan: Add OTel middleware and exporters; propagate trace context; sample Grafana Tempo/Jaeger setup.
  - Accept when: Single request trace spans API → middleware → handlers → external clients.

---

Notes
- All enhancements should maintain backward compatibility and be guarded by environment flags where behavior changes.
- Favor low-cardinality labels in metrics; prefer recording rules for heavy computations.
