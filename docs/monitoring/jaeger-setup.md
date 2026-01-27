# Jaeger Distributed Tracing Setup

Quick guide to get Jaeger distributed tracing running with Forge.

## Overview

Jaeger provides distributed tracing to visualize request flows across services, helping you:
- **Trace requests** end-to-end through the system
- **Identify bottlenecks** in your application
- **Debug latency issues** by seeing where time is spent
- **Understand service dependencies** and call graphs
- **Correlate traces** with logs and metrics

## Prerequisites

- Docker and Docker Compose installed
- Forge backend with OpenTelemetry support
- Monitoring stack running (Prometheus, Grafana, Loki)

## Quick Start

### 1. Start Monitoring Stack (includes Jaeger)

```bash
cd monitoring
docker-compose up -d
```

This starts:
- **Jaeger** (port 16686) - Tracing UI
- **Jaeger Collector** (port 14268) - HTTP endpoint for traces
- **Loki** (port 3100) - Log aggregation
- **Prometheus** (port 9090) - Metrics
- **Grafana** (port 3030) - Visualization

### 2. Configure Forge to Send Traces

Set environment variables in your `.env` file or when starting Forge:

```bash
# Enable tracing
TRACING_ENABLED=true

# Use Jaeger exporter
TRACING_EXPORTER=jaeger

# Jaeger endpoint (use Docker service name or host.docker.internal)
TRACING_ENDPOINT=http://localhost:4318/v1/traces

# Or use legacy Jaeger HTTP endpoint
# TRACING_ENDPOINT=http://localhost:14268/api/traces

# Sample rate (0.0 to 1.0, 1.0 = 100% of requests)
TRACING_SAMPLE_RATE=0.1  # 10% sampling (recommended for production)

# Service name
TRACING_SERVICE_NAME=forge-server

# Service version
TRACING_SERVICE_VERSION=1.0.0
```

### 3. Verify Services

```bash
# Check Jaeger is running
docker ps | grep jaeger

# Should see:
# forge-jaeger  Up  16686/tcp, 14268/tcp, 6831/udp, 6832/udp
```

### 4. Access Jaeger UI

1. Open: http://localhost:16686
2. You should see the Jaeger UI
3. Select service: `forge-server` (or your service name)
4. Click "Find Traces"

### 5. Generate Some Traffic

Make some requests to your Forge API:

```bash
# Example: Create a conversation
curl -X POST http://localhost:3000/api/conversation \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

Then check Jaeger UI - you should see traces appearing!

## Configuration Options

### Sampling Rate

Control how many requests are traced:

```bash
# 100% sampling (all requests) - use for debugging
TRACING_SAMPLE_RATE=1.0

# 10% sampling (recommended for production)
TRACING_SAMPLE_RATE=0.1

# 1% sampling (high traffic)
TRACING_SAMPLE_RATE=0.01
```

### Endpoint Configuration

**Option 1: OTLP HTTP (Recommended)**
```bash
TRACING_EXPORTER=jaeger
TRACING_ENDPOINT=http://localhost:4318/v1/traces
```

**Option 2: Legacy Jaeger HTTP**
```bash
TRACING_EXPORTER=jaeger
TRACING_ENDPOINT=http://localhost:14268/api/traces
```

**Option 3: UDP Agent (Legacy)**
```bash
TRACING_EXPORTER=jaeger
JAEGER_AGENT_HOST=localhost
JAEGER_AGENT_PORT=6831
```

### Docker Network Configuration

If Forge runs in Docker, use service name:

```bash
# In docker-compose.yml or Docker network
TRACING_ENDPOINT=http://jaeger:4318/v1/traces
```

If Forge runs on host, use `host.docker.internal`:

```bash
# On macOS/Windows
TRACING_ENDPOINT=http://host.docker.internal:4318/v1/traces

# On Linux
TRACING_ENDPOINT=http://172.17.0.1:4318/v1/traces
```

## Using Jaeger UI

### Finding Traces

1. **Select Service**: Choose your service (e.g., `forge-server`)
2. **Select Operation**: Filter by operation (e.g., `HTTP POST /api/conversation`)
3. **Set Time Range**: Choose time window
4. **Click "Find Traces"**

### Viewing Trace Details

Click on a trace to see:
- **Timeline View**: Visual timeline of spans
- **Span Details**: Attributes, tags, logs
- **Service Map**: Dependency graph
- **Trace Statistics**: Duration breakdown

### Key Features

- **Search**: Filter by tags, duration, errors
- **Compare**: Compare multiple traces
- **Dependencies**: View service dependency graph
- **System Architecture**: Visualize service topology

## Trace Correlation

### With Logs (Loki)

Traces include `trace_id` that can be used to find related logs:

```logql
# In Grafana Explore (Loki)
{job="forge"} |= "trace_id=abc123def456"
```

### With Metrics (Prometheus)

Correlate traces with metrics using:
- `request_id` - Links traces to request metrics
- `conversation_id` - Links traces to conversation metrics
- `trace_id` - Unique trace identifier

## Advanced Configuration

### Custom Span Attributes

Add custom attributes to spans in your code:

```python
from forge.core.tracing import get_tracer

tracer = get_tracer()

with tracer.start_as_current_span("my_operation") as span:
    span.set_attribute("user.id", user_id)
    span.set_attribute("conversation.id", conversation_id)
    span.set_attribute("agent.type", agent_type)
    # ... your code ...
```

### Error Tracking

Errors are automatically recorded in spans:

```python
from forge.core.tracing import get_tracer

tracer = get_tracer()

with tracer.start_as_current_span("risky_operation") as span:
    try:
        # ... your code ...
    except Exception as e:
        span.record_exception(e)
        span.set_attribute("error", True)
        raise
```

### Nested Spans

Create child spans for detailed tracing:

```python
from forge.core.tracing import get_tracer

tracer = get_tracer()

with tracer.start_as_current_span("parent_operation") as parent:
    parent.set_attribute("parent.attr", "value")
    
    with tracer.start_as_current_span("child_operation") as child:
        child.set_attribute("child.attr", "value")
        # ... child operation ...
```

## Troubleshooting

### No Traces Appearing

**1. Check tracing is enabled:**
```bash
# Verify environment variable
echo $TRACING_ENABLED
# Should be: true
```

**2. Check Jaeger is accessible:**
```bash
# Test Jaeger UI
curl http://localhost:16686
# Should return HTML

# Test collector endpoint
curl http://localhost:14268/api/traces
# Should return 405 (Method Not Allowed is OK)
```

**3. Check Forge logs:**
```bash
# Look for tracing initialization
grep -i "tracing" logs/Forge.log

# Should see:
# "Tracing initialized: service=forge-server, exporter=jaeger, ..."
```

**4. Verify OpenTelemetry packages:**
```bash
# Check if packages are installed
poetry show | grep opentelemetry

# Should see:
# opentelemetry-api
# opentelemetry-sdk
# opentelemetry-exporter-otlp
```

### Traces Not Complete

**1. Check sampling rate:**
```bash
# If too low, increase it
TRACING_SAMPLE_RATE=1.0  # 100% for debugging
```

**2. Check span propagation:**
- Ensure spans are properly nested
- Check for context propagation issues
- Verify async context is preserved

### High Overhead

**1. Reduce sampling:**
```bash
# Lower sampling rate
TRACING_SAMPLE_RATE=0.01  # 1% sampling
```

**2. Filter operations:**
```bash
# Only trace specific routes
OTEL_SAMPLE_ROUTES="/api/conversation"
```

## Performance Considerations

### Sampling Strategy

- **Development**: 100% sampling (see everything)
- **Production**: 10% sampling (balanced)
- **High Traffic**: 1% sampling (minimal overhead)

### Storage

Jaeger all-in-one uses in-memory storage by default. For production:
- Use Jaeger with persistent storage (Elasticsearch, Cassandra)
- Configure retention policies
- Consider using Tempo (Grafana's tracing backend)

## Integration with Grafana

### View Traces in Grafana

1. Install Tempo datasource (or use Jaeger plugin)
2. Configure Tempo to read from Jaeger
3. Create trace panels in dashboards
4. Correlate traces with metrics and logs

### Trace-to-Metrics Correlation

Link traces to Prometheus metrics:
- Use `request_id` to find related metrics
- Use `trace_id` to find related logs
- Create dashboards showing trace duration vs metrics

## Next Steps

1. ✅ Set up distributed tracing (you're here!)
2. ⏭️ Configure trace sampling strategies
3. ⏭️ Create custom spans for key operations
4. ⏭️ Set up trace-based alerts
5. ⏭️ Integrate with Grafana for unified observability

## Resources

- **Jaeger Docs:** https://www.jaegertracing.io/docs/
- **OpenTelemetry Python:** https://opentelemetry.io/docs/instrumentation/python/
- **Trace Best Practices:** https://opentelemetry.io/docs/specs/otel/trace/

---

**Distributed tracing enabled! 🎉**

