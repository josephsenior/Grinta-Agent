# Monitoring Guide

## Overview

Forge includes comprehensive production-grade monitoring with:
- **3 Grafana Dashboards** - Visual metrics and trends
- **30+ Prometheus Metrics** - Operational telemetry
- **6 Alerting Rules** - Proactive issue detection
- **7 Frontend Components** - Real-time monitoring UI
- **Structured JSON Logging** - Request tracing and debugging

## Quick Start

### Start Monitoring Stack

docker-compose up -d
```bash
cd monitoring
docker compose up -d  # uses base + optional override
```

Optional: copy the example override and adjust targets if not using host.docker.internal:

```bash
cp docker-compose.override.example.yml docker-compose.override.yml
docker compose up -d --force-recreate prometheus grafana
```

**Services Started:**
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001` (admin/admin) - Note: Grafana runs on port 3001, separate from the Forge backend which runs on port 3000

### Access Dashboards

1. Open Grafana: `http://localhost:3001`
2. Login: `admin` / `admin`
3. Navigate to Dashboards:
   - LLM Performance
   - System Metrics
   - Error Tracking

## Grafana Dashboards

### 1. LLM Performance Dashboard

**File:** `monitoring/grafana/dashboards/llm-performance.json`

**Panels:**
- **LLM Latency** - Response times (p50, p90, p95, p99)
- **Token Usage** - Input/output tokens over time
- **Cost Tracking** - LLM costs per model
- **Model Distribution** - Which models are being used
- **Cache Hit Rate** - Prompt caching efficiency

**Key Metrics:**
```
metasop_step_duration_ms_p95    # 95th percentile latency
metasop_total_tokens            # Total token consumption
metasop_model_total_tokens{model="claude-4"}  # Per-model tokens
metasop_cache_hits / (metasop_cache_hits + metasop_cache_stores)  # Cache rate
```

**What to Watch:**
- p95 latency > 2000ms → Slow responses
- Cache hit rate < 30% → Poor caching
- Token spikes → Cost issues

### 2. System Metrics Dashboard

**File:** `monitoring/grafana/dashboards/system-metrics.json`

**Panels:**
- **Active Conversations** - Current active sessions
- **CPU Usage** - System resource utilization
- **Memory Usage** - RAM consumption
- **Request Rate** - Requests per second
- **Success Rate** - Successful vs failed requests

**What to Watch:**
- CPU > 80% → Need more resources
- Memory growing → Potential leak
- Success rate < 90% → System issues

### 3. Error Tracking Dashboard

**File:** `monitoring/grafana/dashboards/error-tracking.json`

**Panels:**
- **Error Rate** - Percentage of failed requests
- **Error Types** - Distribution of error types
- **Failed Actions** - Which actions are failing
- **Retry Attempts** - Retry patterns

**What to Watch:**
- Error rate > 5% → System degradation
- Specific action failing repeatedly → Bug
- High retry rate → Unstable dependencies

## Prometheus Metrics Reference

### Request/HTTP Metrics

```
forge_build_info{version="...",git_sha="..."} 1          # Build metadata
forge_request_total                                   # Total HTTP requests seen
forge_request_exceptions_total                        # Requests resulting in exceptions
forge_requests_in_flight                              # Currently active requests
forge_request_duration_ms_bucket{le="..."}           # Latency histogram buckets (ms)
forge_request_duration_ms_sum                         # Latency histogram sum
forge_request_duration_ms_count                       # Latency histogram count
forge_request_bytes_total                             # Sum of request bytes (via Content-Length)
forge_response_bytes_total                            # Sum of response bytes

forge_request_total{method="...",status="...",route="..."}  # Per-route counters
```

Notes:
- Byte counters are lightweight and rely on `Content-Length` when present; streaming bodies are not buffered.
- Access logs include per-request `request_content_length` and `response_content_length` on the `forge.access` channel.

### PromQL Examples: Method/Status

Requests per second by method (exclude internal `exception` pseudo-status):

```promql
sum by (method) (rate(forge_request_total{status!="exception"}[5m]))
```

Error rate (5xx) overall and by method:

```promql
# Overall 5xx error rate (% of all requests)
100 * sum(rate(forge_request_total{status=~"5.."}[5m]))
  / sum(rate(forge_request_total{status!="exception"}[5m]))

# By method
100 * sum by (method) (rate(forge_request_total{status=~"5.."}[5m]))
  / sum by (method) (rate(forge_request_total{status!="exception"}[5m]))
```

Success rate (2xx and 3xx) overall and by method:

```promql
# Overall success rate
100 * sum(rate(forge_request_total{status=~"2..|3.."}[5m]))
  / sum(rate(forge_request_total{status!="exception"}[5m]))

# By method
100 * sum by (method) (rate(forge_request_total{status=~"2..|3.."}[5m]))
  / sum by (method) (rate(forge_request_total{status!="exception"}[5m]))
```

4xx vs 5xx split (requests per second):

```promql
sum(rate(forge_request_total{status=~"4.."}[5m]))  # client errors
sum(rate(forge_request_total{status=~"5.."}[5m]))  # server errors
```

Top methods by 5xx volume:

```promql
topk(3, sum by (method) (rate(forge_request_total{status=~"5.."}[5m])))
```

Unhandled exception rate (not mapped to an HTTP status):

```promql
rate(forge_request_total{status="exception"}[5m])
```

Note: The `exception` status represents unhandled errors before an HTTP response is produced; consider whether to include or exclude it in SLI calculations.

### PromQL Examples: Route-Level

Top endpoints by request rate (normalized by route template):

```promql
topk(10, sum by (route) (rate(forge_request_total{status!="exception"}[5m])))
```

Slowest endpoints by p95 latency (approximate via histogram quantile):

```promql
histogram_quantile(
  0.95,
  sum by (le, route) (rate(forge_request_duration_ms_bucket[5m]))
) by (route)
```

Error rate by route (5xx / all):

```promql
100 * sum by (route) (rate(forge_request_total{status=~"5.."}[5m]))
  / sum by (route) (rate(forge_request_total{status!="exception"}[5m]))
```

Top routes by response bytes (egress):

```promql
topk(5, sum by (route) (rate(forge_response_bytes_total[5m])))
```

### Runtime Pool Metrics

```
forge_runtime_warm_pool_total                      # Total warm sandboxes staged for reuse
forge_runtime_warm_pool{kind="docker"}            # Warm capacity by runtime kind
forge_runtime_running_sessions_total              # Active runtime sessions across all kinds
forge_runtime_running_sessions{kind="remote"}     # Active sessions by runtime kind
```

**PromQL examples:**

```promql
# Alert when Docker warm capacity drops below 2 instances
forge_runtime_warm_pool{kind="docker"} < 2

# Detect leaked remote sessions (sessions that remain active after traffic quiets down)
max_over_time(forge_runtime_running_sessions{kind="remote"}[10m])
```

The runtime manager updates the snapshot whenever Local, Docker, or Remote runtimes acquire warm sandboxes or attach live sessions, giving immediate visibility into pool pressure and potential leaks.

### Steps & Execution

```
metasop_steps_executed       # Total steps executed successfully
metasop_steps_failed         # Failed step count
metasop_steps_timed_out      # Steps that timed out
metasop_suppressed_errors    # Errors handled gracefully
```

### Latency & Performance

```
metasop_step_duration_ms_bucket{le="50"}    # Histogram buckets
metasop_step_duration_ms_sum                # Total duration
metasop_step_duration_ms_count              # Step count
metasop_step_duration_ms_p50                # Median latency
metasop_step_duration_ms_p90                # 90th percentile
metasop_step_duration_ms_p95                # 95th percentile  
metasop_step_duration_ms_p99                # 99th percentile
```

**Per-Role Latency:**
```
metasop_step_duration_ms_role_p95{role="Engineer"}    # Engineer latency
metasop_step_duration_ms_role_p95{role="Architect"}  # Architect latency
```

### Token Usage & Costs

```
metasop_total_tokens                        # All tokens consumed
metasop_model_total_tokens{model="..."}     # Per-model tokens
metasop_avg_tokens_per_executed_step        # Average tokens per step
```

**Calculate costs:**
```promql
# Total cost (example for Claude Sonnet @ $3 input, $15 output)
(metasop_total_tokens * 0.009)  # Assuming 50/50 input/output
```

### Caching

```
metasop_cache_hits        # Cache hits
metasop_cache_stores      # Cache stores
metasop_cache_entries     # Current cache size
metasop_cache_evictions   # Cache evictions
```

**Cache hit rate:**
```promql
metasop_cache_hits / (metasop_cache_hits + metasop_cache_stores) * 100
```

### Retry & Reliability

```
metasop_retry_attempts                      # Total retry attempts
metasop_retry_successes                     # Successful retries
metasop_retry_failures                      # Failed retries
metasop_retry_attempts_by_operation{op="..."} # Per-operation retries
```

### Context Management

```
metasop_context_unique       # Unique contexts (cache misses)
metasop_context_reuse_total  # Reused contexts (cache hits)
metasop_diff_unique          # Unique diffs
metasop_diff_reuse_total     # Reused diffs
```

## Alerting Rules

**File:** `monitoring/grafana/provisioning/alerting/rules.yml`

### 1. High Error Rate (Critical)

**Trigger:** Error rate > 5% for 5 minutes

**Formula:**
```promql
(metasop_steps_failed / (metasop_steps_executed + metasop_steps_failed)) * 100 > 5
```

**Action:** Investigate failing steps immediately

### 2. Slow Response Time (Warning)

**Trigger:** p95 latency > 2000ms for 10 minutes

**Formula:**
```promql
metasop_step_duration_ms_p95 > 2000
```

**Action:** Check LLM provider status, optimize prompts

### 3. Low Cache Hit Rate (Info)

**Trigger:** Cache hit rate < 30% for 15 minutes

**Formula:**
```promql
(metasop_cache_hits / (metasop_cache_hits + metasop_cache_stores)) * 100 < 30
```

**Action:** Review caching strategy, check cache eviction rate

### 4. Service Down (Critical)

**Trigger:** Service not responding for 2 minutes

**Formula:**
```promql
up{job="forge-metasop"} < 1
```

**Action:** Restart service, check logs for crash

### 5. High Retry Rate (Warning)

**Trigger:** Retry rate > 20% for 10 minutes

**Formula:**
```promql
(metasop_retry_attempts / metasop_steps_executed) * 100 > 20
```

**Action:** Investigate unstable operations, check external dependencies

### 6. High Token Usage (Info)

**Trigger:** Token rate > 1000 tokens/sec for 30 minutes

**Formula:**
```promql
rate(metasop_total_tokens[1h]) > 1000
```

**Action:** Review token consumption, check for runaway agents

## Frontend Monitoring Components

### Live Metrics Cards

**File:** `frontend/src/components/features/monitoring/live-metrics-cards.tsx`

**Displays:**
- Error Rate (real-time)
- High-Risk Actions
- Progress
- Iterations/Minute
- Avg Response Time
- Security Score

**Usage:**
```typescript
<LiveMetricsCards 
  metrics={{
    errorRate: 2.5,
    highRiskActions: 0,
    progress: 75,
    iterationsPerMinute: 12,
    avgResponseTime: 850,
    securityScore: 98
  }}
/>
```

### Autonomous Monitor

**File:** `frontend/src/components/features/monitoring/autonomous-monitor.tsx`

Real-time agent activity monitoring

### Risk Level Chart

**File:** `frontend/src/components/features/monitoring/risk-level-chart.tsx`

Visualizes security risk distribution

### Safety Score Gauge

**File:** `frontend/src/components/features/monitoring/safety-score-gauge.tsx`

Overall safety score (0-100)

### Enhanced Audit Trail

**File:** `frontend/src/components/features/monitoring/enhanced-audit-trail.tsx`

Complete action history with timestamps

## Structured Logging

### Log Format

**JSON Logs** (enabled by default):

```json
{
  "timestamp": "2025-11-04T10:15:30.123Z",
  "level": "INFO",
  "message": "Agent step completed",
  "request_id": "req_abc123",
  "conversation_id": "conv_456def",
  "agent_type": "CodeActAgent",
  "action_type": "FileEditAction",
  "model_used": "claude-sonnet-4-20250514",
  "tokens_consumed": 1500,
  "cost_usd": 0.015,
  "duration_ms": 850
}
```

### Request Tracing

**All logs include `request_id` for end-to-end tracing:**

```bash
# Trace single request through entire system
tail -f logs/Forge.log | grep "request_id=req_abc123"

# Output shows:
# [Request received] request_id=req_abc123
# [Agent invoked] request_id=req_abc123 agent=CodeActAgent
# [LLM called] request_id=req_abc123 model=claude-4 tokens=1500
# [Action executed] request_id=req_abc123 action=FileEditAction
# [Response sent] request_id=req_abc123 duration_ms=850
```

### Log Levels

```
DEBUG - Detailed debugging (dev only)
INFO  - Normal operations (production default)
WARN  - Potential issues
ERROR - Actual errors
```

**Configure:**
```bash
# In .env:
LOG_LEVEL=INFO
LOG_JSON=true
```

## Metrics API

### Get System Metrics

```http
GET /api/monitoring/metrics
```

**Response:**
```json
{
  "system": {
    "timestamp": "2025-11-04T10:00:00Z",
    "active_conversations": 5,
    "total_actions_today": 1234,
    "avg_response_time_ms": 850,
    "cache_stats": {
      "hits": 456,
      "stores": 123,
      "hit_rate": 78.8,
      "entries": 250,
      "evictions": 12
    }
  },
  "agents": [
    {
      "agent_name": "CodeActAgent",
      "total_actions": 1000,
      "successful_actions": 950,
      "success_rate": 95.0,
      "avg_action_time_ms": 800
    }
  ]
}
```

## Best Practices
## Readiness Probe

Endpoint for container healthchecks and orchestrators:

```http
GET /api/monitoring/readiness
```

Response includes status and dependency checks:

```json
{
  "status": "ready",
  "timestamp": "2025-11-11T10:00:00Z",
  "checks": {
    "redis": { "status": "up" },
    "mcp": { "status": "skipped" }
  }
}
```

Configuration:
- `REDIS_URL` or `REDIS_CONNECTION_URL`: if set, performs a `PING` check.
- `ACTION_EXECUTION_SERVER_URL`: if set, checks `GET /alive` on that service.

Docker Compose healthcheck (example):

```yaml
healthcheck:
  test: ["CMD", "curl", "-fsS", "http://localhost:3000/api/monitoring/readiness"]
  interval: 30s
  timeout: 3s
  retries: 3
  start_period: 10s
```


### 1. Monitor Key Metrics

**Essential metrics to watch:**
- Error rate (should be < 5%)
- p95 latency (should be < 2s)
- Cache hit rate (should be > 30%)
- Token usage (watch for spikes)

### 2. Set Up Alerts

**Critical alerts:**
- Service down → Immediate page
- High error rate → Page during business hours
- Slow response → Email notification

**Configure in Grafana:**
1. Go to Alerting → Alert rules
2. Edit existing rules
3. Add contact points (email, Slack, PagerDuty)

### 3. Regular Reviews

**Daily:**
- Check error rates in Grafana
- Review high-cost conversations
- Monitor token consumption

**Weekly:**
- Analyze performance trends
- Review alert history
- Optimize expensive queries

**Monthly:**
- Review total costs
- Analyze user patterns
- Plan capacity

### 4. Log Analysis

**Useful log queries:**

```bash
# Find errors
grep "ERROR" logs/Forge.log

# Find slow requests
grep "duration_ms" logs/Forge.log | awk '$NF > 3000'

# Find expensive requests
grep "cost_usd" logs/Forge.log | awk '$NF > 1.0'

# Track specific user
grep "user_id=user_123" logs/Forge.log
```

## Troubleshooting Monitoring

### Grafana Not Showing Data

**Check Prometheus:**
```bash
# Verify Prometheus can scrape metrics
curl http://localhost:9090/metrics

# Check Prometheus targets
open http://localhost:9090/targets
```

### Metrics Not Updating

**Check metrics server:**
```bash
# Metrics exposed on port 9090
curl http://localhost:9090/metrics | grep metasop

# Should see 30+ metrics
```

### Alerts Not Firing

**Check alert rules:**
```bash
# In Grafana:
# Alerting → Alert rules → Check state

# Common issues:
# - Threshold too high
# - Data source not connected
# - Contact point not configured
```

## Advanced Monitoring

### Custom Metrics

**Add your own metrics:**

```python
# In Forge/metasop/metrics.py
from forge.metasop.metrics import get_metrics_registry

metrics = get_metrics_registry()
metrics.record_event({
    'status': 'executed',
    'duration_ms': 1500,
    'total_tokens': 2000,
    'model': 'claude-4',
    'role': 'Engineer'
})
```

### Custom Dashboards

**Create new dashboard:**

1. Go to Grafana
2. Create → Dashboard
3. Add Panel
4. Select Prometheus data source
5. Write PromQL query
6. Save dashboard

**Example query:**
```promql
# Average latency by model
avg(metasop_step_duration_ms_p95) by (model)

# Token consumption rate
rate(metasop_total_tokens[5m])

# Error rate
(metasop_steps_failed / (metasop_steps_executed + metasop_steps_failed)) * 100
```

### Export Metrics

**For external systems:**

```bash
# Prometheus format
curl http://localhost:9090/metrics > metrics.txt

# JSON format
curl http://localhost:3000/api/monitoring/metrics > metrics.json
```

## Cost Monitoring

### Track LLM Costs

**In Grafana:**
- LLM Performance → Cost Tracking panel
- Shows cost per model over time

**Via API:**
```http
GET /api/analytics/usage?period=week
```

**Response:**
```json
{
  "period": "week",
  "cost_usd": 12.34,
  "tokens": {
    "input": 1500000,
    "output": 500000
  },
  "breakdown_by_model": [
    {
      "model": "claude-sonnet-4",
      "cost_usd": 8.50,
      "tokens": 1200000
    }
  ]
}
```

### Cost Alerts

**Set budget alerts:**

1. Go to Grafana → Alerting
2. Create new alert rule
3. Query: `sum(cost_per_hour) > 10`
4. Alert when hourly cost exceeds $10

## Performance Optimization

### Based on Metrics

**If p95 latency > 2s:**
1. Check which step is slow
2. Review prompt size
3. Consider faster model (Claude Haiku 4.5)
4. Enable caching

**If cache hit rate < 30%:**
1. Review cache TTL settings
2. Check cache eviction rate
3. Increase cache size

**If token usage spiking:**
1. Check conversation history size
2. Enable memory condensation
3. Reduce max_message_chars

## Monitoring Checklist

### Daily
- [ ] Check Grafana dashboards (5 min)
- [ ] Review error rate (should be < 5%)
- [ ] Check for new alerts

### Weekly
- [ ] Analyze performance trends
- [ ] Review cost breakdown
- [ ] Check alert history
- [ ] Optimize based on patterns

### Monthly
- [ ] Review total costs vs budget
- [ ] Analyze user behavior patterns
- [ ] Plan capacity (if growing)
- [ ] Update alert thresholds

## References

- [Architecture](./ARCHITECTURE.md) - System overview
- [Troubleshooting](./TROUBLESHOOTING.md) - Debug issues
- [Performance Tuning](./guides/performance-tuning.md) - Optimization guide

## Monitoring Resources

- **Prometheus Docs:** https://prometheus.io/docs/
- **Grafana Docs:** https://grafana.com/docs/
- **PromQL Tutorial:** https://prometheus.io/docs/prometheus/latest/querying/basics/

For questions about monitoring, see [Troubleshooting](./TROUBLESHOOTING.md) or open a GitHub issue.


## Operators Appendix

### ACCESS Log Fields

- message: High-level event, e.g. "Request started: GET /path", "Request completed: GET /path", "Request sizes"
- request_id: Correlation ID for end-to-end tracing
- method: HTTP method (GET, POST, ...)
- path: Request path (no query string)
- status_code: Response status (on completion)
- duration_ms: End-to-end request time in milliseconds (on completion)
- client_host: Remote address (on start)
- user_agent: User agent string (on start)
- request_content_length: Bytes from request `Content-Length` header, if present
- response_content_length: Bytes from response `Content-Length` header (or body length when safe)

### Sample Queries (CLI)

Tail access logs only (JSON format assumed):

```bash
grep '"forge.access"' logs/Forge.log
```

Top endpoints by request volume:

```bash
jq -r 'select(.message|startswith("Request completed")) | .path' logs/Forge.log \
  | sort | uniq -c | sort -nr | head
```

p95 request latency (approximate via awk):

```bash
jq -r 'select(.message|startswith("Request completed")) | .duration_ms' logs/Forge.log \
  | sort -n | awk 'BEGIN{p=95} {a[NR]=$1} END{print a[int(NR*p/100)]}'
```

Requests over 1 MB response size:

```bash
jq -r 'select(.message=="Request sizes" and (.response_content_length // 0) > (1024*1024)) | {path, response_content_length}' logs/Forge.log
```

Error rate by status:

```bash
jq -r 'select(.message|startswith("Request completed")) | .status_code' logs/Forge.log \
  | awk '{c[$1]++} END{for (k in c) print k, c[k]}' | sort -nr
```

Trace a single request_id:

```bash
REQ="<paste-request-id>"; jq -c --arg id "$REQ" 'select(.request_id==$id)' logs/Forge.log
```

