# Loki Log Aggregation Setup

Quick guide to get Loki log aggregation running with Forge.

## Prerequisites

- Docker and Docker Compose installed
- Forge logs directory exists (`logs/` in project root)
- Forge backend configured to write JSON logs

## Quick Start

### 1. Start Monitoring Stack

```bash
cd monitoring
docker-compose up -d
```

This starts:
- **Loki** (port 3100) - Log storage
- **Promtail** (port 9080) - Log shipper
- **Prometheus** (port 9090) - Metrics
- **Grafana** (port 3030) - Visualization

### 2. Verify Services

```bash
# Check all services are running
docker-compose ps

# Should see:
# forge-loki        Up  3100/tcp
# forge-promtail    Up  9080/tcp
# forge-prometheus  Up  9090/tcp
# forge-grafana     Up  3030/tcp
```

### 3. Check Logs Are Being Collected

```bash
# Check Promtail logs
docker logs forge-promtail

# Should see:
# "msg"="Starting Promtail" ...
# "msg"="targets"="[localhost]" ...
```

### 4. Access Grafana

1. Open: http://localhost:3030
2. Login: `admin` / `forge_admin_2025`
3. Go to **Explore** (compass icon)
4. Select **Loki** datasource
5. Try query: `{job="forge"}`

### 5. View Logs Dashboard

1. In Grafana, go to **Dashboards**
2. Open **"Forge Logs Explorer"**
3. You should see logs streaming in real-time!

## Configuration

### Log Directory

Promtail watches logs from:
- `/var/log/forge/*.log` (mapped from `../logs/` in docker-compose)
- `/var/log/forge/llm/**/*.log` (LLM-specific logs)

Ensure Forge is writing logs to the `logs/` directory:
```bash
# Check logs directory exists
ls -la logs/

# Should see:
# Forge.log
# Forge.access.log (if split)
```

### Log Format

Forge should write **JSON logs** for best results. Promtail automatically:
- Parses JSON fields
- Extracts labels (level, request_id, agent_type, etc.)
- Indexes logs for fast searching

Enable JSON logging in Forge:
```bash
# .env file
LOG_JSON=true
LOG_TO_FILE=true
LOG_LEVEL=INFO
```

### Retention

Loki is configured for **30-day retention** by default.

To change retention, edit `monitoring/loki/loki-config.yml`:
```yaml
table_manager:
  retention_period: 720h  # 30 days (change as needed)
```

## LogQL Examples

### Basic Queries

```logql
# All logs
{job="forge"}

# Only errors
{job="forge", level="ERROR"}

# Specific request
{job="forge"} |= "request_id=req_abc123"

# Specific agent
{job="forge", agent_type="CodeActAgent"}
```

### Advanced Queries

```logql
# Count logs by level
sum(count_over_time({job="forge"}[1m])) by (level)

# Error rate
sum(rate({job="forge", level="ERROR"}[5m]))

# Slow requests (>3s)
{job="forge"} | json | duration_ms > 3000

# Search in message
{job="forge"} |= "ConnectionError"

# Multiple conditions
{job="forge", level="ERROR"} |= "timeout" | json
```

## Troubleshooting

### No Logs Appearing

**1. Check Promtail is running:**
```bash
docker ps | grep promtail
docker logs forge-promtail
```

**2. Verify log files exist:**
```bash
ls -la logs/
# Should see Forge.log or similar
```

**3. Check log file permissions:**
```bash
# Promtail needs read access
chmod 644 logs/*.log
```

**4. Verify Loki is accessible:**
```bash
curl http://localhost:3100/ready
# Should return: ready
```

**5. Check Promtail can reach Loki:**
```bash
docker exec forge-promtail wget -qO- http://loki:3100/ready
# Should return: ready
```

### Logs Not Parsing Correctly

**1. Verify JSON format:**
```bash
# Check first log line
head -n 1 logs/Forge.log | jq .
# Should be valid JSON
```

**2. Check Promtail config:**
```bash
# View Promtail config
docker exec forge-promtail cat /etc/promtail/config.yml
```

**3. Test Promtail parsing:**
```bash
# Check Promtail logs for parsing errors
docker logs forge-promtail | grep -i error
```

### High Log Volume

**1. Adjust retention:**
Edit `monitoring/loki/loki-config.yml`:
```yaml
table_manager:
  retention_period: 168h  # 7 days instead of 30
```

**2. Enable log sampling:**
Edit `monitoring/promtail/promtail-config.yml`:
```yaml
scrape_configs:
  - job_name: forge-app
    pipeline_stages:
      - drop:
          expression: '.*'  # Drop all logs (example)
          drop_counter_reason: "sampling"
```

**3. Filter at source:**
Set higher log level in Forge:
```bash
LOG_LEVEL=WARNING  # Only WARNING and above
```

## Performance Tuning

### Loki Limits

Default limits in `loki-config.yml`:
- Ingestion rate: 16 MB/s
- Max line size: 256 KB
- Max streams: 10,000 per user

To increase:
```yaml
limits_config:
  ingestion_rate_mb: 32  # Double the rate
  max_line_size: 512KB   # Double the size
  max_streams_per_user: 20000  # Double streams
```

### Promtail Performance

Promtail is lightweight, but for high volume:
- Increase scrape interval (default: real-time)
- Add more Promtail instances (horizontal scaling)
- Use log sampling

## Next Steps

1. ✅ Set up log aggregation (you're here!)
2. ⏭️ Configure alerting on error logs
3. ⏭️ Set up log retention policies
4. ⏭️ Create custom LogQL queries
5. ⏭️ Integrate with distributed tracing

## Resources

- **Loki Docs:** https://grafana.com/docs/loki/latest/
- **LogQL Guide:** https://grafana.com/docs/loki/latest/logql/
- **Promtail Docs:** https://grafana.com/docs/loki/latest/clients/promtail/

---

**Log aggregation enabled! 🎉**

