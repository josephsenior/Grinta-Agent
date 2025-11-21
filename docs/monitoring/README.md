# Forge Monitoring Stack

Production-grade monitoring for Forge using Prometheus + Grafana.

---

## 🎯 **What's Included**

### **1. Prometheus** (Port 9090)
- Metrics collection from Forge backend
- MetaSOP metrics (latency, tokens, retries)
- 30-day retention
- Self-monitoring

### **2. Grafana** (Port 3030)
- 8 pre-built dashboards:
  - **System Metrics** - Events, cache, retries
  - **LLM Performance** - Latency (p50, p95, p99), tokens
  - **Error & Reliability** - Failures, retries, timeouts
  - **MetaSOP gRPC Services** - RPC latency, error rate, throughput
  - **Logs Explorer** - Centralized log aggregation and search
- Auto-provisioned datasources (Prometheus + Loki)
- Admin user: `admin` / `forge_admin_2025`

### **3. Loki** (Port 3100)
- Log aggregation and storage
- 30-day retention
- LogQL query language
- Integrated with Grafana

### **4. Promtail** (Log Shipper)
- Ships Forge logs to Loki
- Automatic log parsing (JSON support)
- Label extraction from log fields
- Real-time log streaming

### **5. Jaeger** (Port 16686)
- Distributed tracing UI
- Request flow visualization
- Latency analysis
- Service dependency mapping

### **6. Redis** (Port 6379)
- Distributed rate limiting
- Cost quota tracking
- Persistent storage

---

## 🚀 **Quick Start**

### **1. Start Monitoring Stack**
```bash
cd monitoring
docker-compose up -d
```

### **2. Verify Services**
```bash
# Check all services are running
docker-compose ps

# Should see:
# forge-prometheus  Up  9090/tcp
# forge-grafana     Up  3030/tcp
# forge-loki        Up  3100/tcp
# forge-promtail    Up  9080/tcp
# forge-jaeger      Up  16686/tcp, 14268/tcp
# forge-redis       Up  6379/tcp
```

### **3. Configure Forge to Send Metrics**

**MetaSOP Core Metrics**
```toml
# config.toml
[metasop.settings]
metrics_prometheus_port = 9091
```

```bash
export METASOP_PROMETHEUS_PORT=9091
```

**gRPC Adapter Metrics**

The EventService/RuntimeService adapters emit Prometheus metrics when the gRPC feature flag is enabled:

- `metasop_eventservice_rpc_total`
- `metasop_eventservice_rpc_failures_total`
- `metasop_eventservice_rpc_duration_seconds_bucket`
- `metasop_runtime_rpc_total`
- `metasop_runtime_rpc_failures_total`
- `metasop_runtime_rpc_duration_seconds_bucket`

No extra config is required—the metrics are exposed via the same Prometheus endpoint.

### **4. Start Forge Backend**
```bash
# From project root
poetry run python -m Forge.server.listen
```

### **5. Access Dashboards**

**Grafana:** http://localhost:3030
- Username: `admin`
- Password: `forge_admin_2025` (CHANGE THIS!)

**Prometheus:** http://localhost:9090

**Loki:** http://localhost:3100

**Jaeger UI:** http://localhost:16686

---

## 📊 **Dashboards**

### **1. Logs Explorer** (forge-logs)
- Real-time log streaming
- Log volume by level
- Error rate tracking
- Request tracing by request_id
- Agent type filtering
- JSON log parsing
- LogQL query support

### **2. System Metrics** (forge-system)
- Total events counter
- Event rate (events/sec)
- Status distribution (pie chart)
- Cache hit rate gauge
- Retry attempts
- Retry failures

### **3. LLM Performance** (forge-llm)
- Latency percentiles (p50, p90, p95, p99)
- Total tokens counter
- Token usage by model (pie chart)
- Average tokens per step
- Token rate over time

### **4. Error & Reliability** (forge-errors)
- Error rate percentage
- Failed steps counter
- Success vs failure rate
- Retry success rate
- Retry attempts by operation
- Suppressed errors

### **5. MetaSOP gRPC Services** (metasop-grpc)

### **6. Distributed Tracing (Jaeger)**
- Access via Jaeger UI: http://localhost:16686
- View request traces end-to-end
- Analyze latency and bottlenecks
- Correlate with logs and metrics
- p95 RPC latency by method (EventService & RuntimeService)
- Error rate % per service
- Request rate (req/sec)
- RunStep status distribution

---

## ⚙️ **Configuration**

### **Prometheus Scrape Targets**

Edit `prometheus/prometheus.yml`:

```yaml
scrape_configs:
  # MetaSOP metrics
  - job_name: 'forge-metasop'
    static_configs:
      - targets: ['host.docker.internal:9091']
        
  # REST API metrics
  - job_name: 'forge-api'
    metrics_path: '/api/monitoring/metrics'
    static_configs:
      - targets: ['host.docker.internal:3000']

  # gRPC adapters (if running out-of-process)
  - job_name: 'forge-eventservice-grpc'
    static_configs:
      - targets: ['event-service:50051']

  - job_name: 'forge-runtime-grpc'
    static_configs:
      - targets: ['runtime-service:50052']
```

**Note:** Use `host.docker.internal` on macOS/Windows, or `172.17.0.1` on Linux.

### **Grafana Admin Password**

**CRITICAL:** Change default password!

```bash
# Edit docker-compose.yml
environment:
  - GF_SECURITY_ADMIN_PASSWORD=your_secure_password_here
```

Then restart:
```bash
docker-compose restart grafana
```

---

## 🔍 **Verify Metrics**

### **1. Check Prometheus Targets**
```bash
# Open: http://localhost:9090/targets
# All targets should show "UP"
```

### **2. Query Metrics Directly**
```bash
# Prometheus UI: http://localhost:9090/graph
# Try queries:
metasop_total_events
metasop_step_duration_ms_p95
metasop_cache_hits / (metasop_cache_hits + metasop_cache_stores)
```

### **3. Verify Grafana Connection**
```bash
# Grafana → Configuration → Data Sources
# "Prometheus" should be green (working)
```

---

## 📈 **Useful Prometheus Queries**

### **Error Rate (%)**
```promql
(metasop_steps_failed / (metasop_steps_executed + metasop_steps_failed)) * 100
```

### **Cache Hit Rate (%)**
```promql
(metasop_cache_hits / (metasop_cache_hits + metasop_cache_stores)) * 100
```

### **Retry Success Rate (%)**
```promql
(metasop_retry_successes / metasop_retry_attempts) * 100
```

### **Event Rate (events/sec)**
```promql
rate(metasop_total_events[5m])
```

### **Token Rate by Model (tokens/sec)**
```promql
rate(metasop_model_total_tokens[5m])
```

---

## 🛑 **Stop Monitoring**

```bash
cd monitoring
docker-compose down

# To remove volumes (deletes metrics data):
docker-compose down -v
```

---

## 🐛 **Troubleshooting**

### **Metrics Not Showing Up**

**1. Check if Forge is sending metrics:**
```bash
# Verify MetaSOP Prometheus server is running
curl http://localhost:9091/metrics

# Should see metrics like:
# metasop_total_events 123
# metasop_step_duration_ms_p95 1234.0
```

**2. Check Prometheus targets:**
```bash
# Open: http://localhost:9090/targets
# All should be "UP"
# If DOWN, check host.docker.internal resolution
```

**3. Check Grafana datasource:**
```bash
# Grafana → Configuration → Data Sources → Prometheus
# Click "Test" - should be green
```

### **Grafana Shows "No Data"**

**1. Select correct time range:**
- Top-right corner → Last 15 minutes
- Or use "Last 1 hour" if just started

**2. Check dashboard variables:**
- Some dashboards use variables
- Ensure they're set correctly

**3. Verify Prometheus has data:**
```bash
# Query directly in Prometheus:
# http://localhost:9090/graph
# Query: metasop_total_events
# Should return data
```

### **Redis Connection Issues**

**1. Check Redis is running:**
```bash
docker-compose ps redis
# Should show "Up"
```

**2. Test connection:**
```bash
docker exec -it forge-redis redis-cli ping
# Should return: PONG
```

**3. Configure Forge to use Redis:**
```bash
# .env file
REDIS_HOST=localhost
REDIS_PORT=6379
RATE_LIMITING_ENABLED=true
COST_QUOTA_ENABLED=true
```

---

## 📦 **Ports Summary**

| Service | Port | URL |
|---------|------|-----|
| **Grafana** | 3030 | http://localhost:3030 |
| **Prometheus** | 9090 | http://localhost:9090 |
| **Loki** | 3100 | http://localhost:3100 |
| **Promtail** | 9080 | http://localhost:9080 |
| **Jaeger UI** | 16686 | http://localhost:16686 |
| **Jaeger Collector** | 14268 | http://localhost:14268 |
| **Prometheus Metrics (Forge)** | 9091 | http://localhost:9091/metrics |
| **Redis** | 6379 | redis://localhost:6379 |
| **Forge Backend** | 3000 | http://localhost:3000 |

---

## 🔐 **Security Notes**

**For Production:**

1. **Change Grafana password** (default: `forge_admin_2025`)
2. **Enable HTTPS** for Grafana (use nginx/traefik)
3. **Restrict Prometheus access** (use authentication)
4. **Set Redis password:**
   ```yaml
   # docker-compose.yml
   redis:
     command: redis-server --requirepass your_secure_password
   ```
5. **Use environment variables** for secrets

---

## 📊 **Metrics Reference**

### **Counters** (Always increase)
- `metasop_total_events` - Total events processed
- `metasop_steps_executed` - Successful steps
- `metasop_steps_failed` - Failed steps
- `metasop_total_tokens` - Total tokens used
- `metasop_cache_hits` - Cache hits
- `metasop_retry_attempts` - Retry attempts

### **Gauges** (Can go up/down)
- `metasop_cache_entries` - Current cache size
- `metasop_avg_tokens_per_executed_step` - Average tokens

### **Histograms** (Latency tracking)
- `metasop_step_duration_ms` - Step duration (ms)
- `metasop_step_duration_ms_p50` - Median latency
- `metasop_step_duration_ms_p95` - 95th percentile
- `metasop_step_duration_ms_p99` - 99th percentile

### **gRPC Adapter Metrics**
- `metasop_eventservice_rpc_total`, `metasop_eventservice_rpc_failures_total`
- `metasop_runtime_rpc_total`, `metasop_runtime_rpc_failures_total`
- `metasop_eventservice_rpc_duration_seconds_bucket` (histogram)
- `metasop_runtime_rpc_duration_seconds_bucket` (histogram)
- Recording rules: `forge_eventservice_rpc_rate_5m`, `forge_runtime_rpc_rate_5m`,
  `forge_eventservice_error_rate_5m`, `forge_runtime_error_rate_5m`

---

## 🎓 **Learning Resources**

**Prometheus:**
- Query basics: https://prometheus.io/docs/prometheus/latest/querying/basics/
- PromQL examples: https://prometheus.io/docs/prometheus/latest/querying/examples/

**Grafana:**
- Dashboard guide: https://grafana.com/docs/grafana/latest/dashboards/
- Panel types: https://grafana.com/docs/grafana/latest/panels-visualizations/

---

## 🚀 **Next Steps**

**After setup:**
1. ✅ Start monitoring stack
2. ✅ Configure Forge to send metrics
3. ✅ Open Grafana dashboards
4. ⚠️ Change default Grafana password
5. ⚠️ Set up alerts (optional)
6. ⚠️ Configure retention policies

**Optional enhancements:**
- Set up Slack/PagerDuty alerting (see [alerting-integrations.md](./alerting-integrations.md))
- Add Alert Manager for notifications
- Enable Grafana OAuth/SSO
- Set up log retention policies
- Configure log sampling for high-volume scenarios
- Integrate Jaeger traces with Grafana (Tempo plugin)

---

## 📝 **LogQL Examples**

### **Find All Errors**
```logql
{job="forge", level="ERROR"}
```

### **Search for Specific Request**
```logql
{job="forge"} |= "request_id=req_abc123"
```

### **Count Logs by Level**
```logql
sum(count_over_time({job="forge"}[1m])) by (level)
```

### **Find Slow Requests**
```logql
{job="forge"} | json | duration_ms > 3000
```

### **Filter by Agent Type**
```logql
{job="forge", agent_type="CodeActAgent"}
```

### **Error Rate Over Time**
```logql
sum(rate({job="forge", level="ERROR"}[5m]))
```

---

*Monitoring stack ready! Log aggregation enabled! 🚀*

