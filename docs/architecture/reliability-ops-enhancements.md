# Reliability & Operations Enhancements

## Production-Grade Improvements

This document outlines the production-ready enhancements for Forge's reliability and operations infrastructure.

> **Status (Nov 2025):** The first five enhancements are live in the codebase.
> - Redis-backed quotas ship by default (`forge/server/middleware/cost_quota.py`, `forge/server/app.py`).
> - Structured JSON logging with optional shipping and OTEL correlation (`forge/core/logger.py`, `forge/core/log_shipping.py`).
> - Distributed tracing bootstrap (`forge/core/tracing.py`, `forge/server/app.py`).
> - Observability middleware with SLO/alert fan-out (`forge/server/middleware/observability.py`, `forge/core/alerting.py`).
> - Retry queue with adaptive backoff and circuit-breaker integration (`forge/core/retry_queue.py`, `forge/controller/agent_controller.py`).

---

## 1. Redis-Backed Cost Quota Persistence

### Current State
- In-memory `_cost_store` resets on restart → quota abuse possible
- Multi-replica deployments can't share quota state
- `RedisCostQuotaMiddleware` exists but requires manual configuration

### Enhancements

#### 1.1 Default to Redis with Graceful Fallback
- **Auto-detect Redis**: Check for Redis URL in environment
- **Connection Pooling**: Use Redis connection pool for performance
- **Health Checks**: Monitor Redis connection health
- **Graceful Degradation**: Fall back to in-memory if Redis unavailable
- **Retry Logic**: Retry Redis operations with exponential backoff

#### 1.2 Configuration
```python
# forge/core/config/forge_config.py
redis_url: str | None = Field(
    default=None,
    description="Redis connection URL for distributed quota tracking (defaults to REDIS_URL env var)"
)
redis_connection_pool_size: int = Field(
    default=10,
    description="Redis connection pool size"
)
redis_connection_timeout: float = Field(
    default=5.0,
    description="Redis connection timeout in seconds"
)
redis_quota_fallback_enabled: bool = Field(
    default=True,
    description="Fall back to in-memory quota if Redis unavailable"
)
```

#### 1.3 Implementation
- Use `redis.asyncio` with connection pooling
- Implement health checks with automatic reconnection
- Add proper error handling and logging
- Add metrics for Redis operations (latency, errors, fallbacks)

---

## 2. Structured Logging with JSON Format

### Current State
- Standard Python logging (text format)
- No log shipping support
- No structured fields for log aggregation

### Enhancements

#### 2.1 JSON Logging Format
- **Structured Logs**: JSON format for log aggregation
- **Log Levels**: Standard levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Context Fields**: Add trace_id, user_id, request_id, etc.
- **Log Shipping**: Support for external log aggregation (Datadog, ELK, etc.)

#### 2.2 Configuration
```python
# forge/core/config/forge_config.py
log_format: str = Field(
    default="json",
    description="Log format: 'json' or 'text'"
)
log_level: str = Field(
    default="INFO",
    description="Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
)
log_shipping_enabled: bool = Field(
    default=False,
    description="Enable log shipping to external services"
)
log_shipping_endpoint: str | None = Field(
    default=None,
    description="Log shipping endpoint (e.g., Datadog, ELK)"
)
log_shipping_api_key: SecretStr | None = Field(
    default=None,
    description="API key for log shipping service"
)
```

#### 2.3 Implementation
- Use `python-json-logger` for JSON formatting
- Add structured fields to all log entries
- Implement log shipping with async batching
- Add log rotation and retention policies

---

## 3. Distributed Tracing (OpenTelemetry)

### Current State
- OpenTelemetry hooks exist but are optional
- No default exporters configured
- No trace sampling configuration
- No trace context propagation

### Enhancements

#### 3.1 Default Tracing Configuration
- **Auto-instrumentation**: Enable tracing by default
- **Exporters**: Support for Jaeger, Zipkin, OTLP, console
- **Sampling**: Configurable sampling rates
- **Context Propagation**: Automatic trace context propagation
- **Service Name**: Configure service name and version

#### 3.2 Configuration
```python
# forge/core/config/forge_config.py
tracing_enabled: bool = Field(
    default=True,
    description="Enable distributed tracing"
)
tracing_exporter: str = Field(
    default="console",
    description="Tracing exporter: 'jaeger', 'zipkin', 'otlp', 'console'"
)
tracing_endpoint: str | None = Field(
    default=None,
    description="Tracing endpoint URL"
)
tracing_sample_rate: float = Field(
    default=0.1,
    ge=0.0,
    le=1.0,
    description="Trace sampling rate (0.0 to 1.0)"
)
tracing_service_name: str = Field(
    default="forge",
    description="Service name for tracing"
)
tracing_service_version: str = Field(
    default="1.0.0",
    description="Service version for tracing"
)
```

#### 3.3 Implementation
- Use `opentelemetry-api` and `opentelemetry-sdk`
- Add automatic instrumentation for FastAPI, Redis, HTTP clients
- Implement trace context propagation
- Add trace exporters with proper configuration
- Add trace sampling based on configuration

---

## 4. Alert Policies and SLO Tracking

### Current State
- Optional Prometheus metrics server
- No alert policies
- No SLO tracking
- No alerting integration

### Enhancements

#### 4.1 Alert Policies
- **Error Rate Alerts**: Alert on high error rates
- **Latency Alerts**: Alert on high latency
- **Quota Alerts**: Alert on quota exhaustion
- **Circuit Breaker Alerts**: Alert on circuit breaker trips
- **Health Check Alerts**: Alert on health check failures

#### 4.2 SLO Tracking
- **Availability SLO**: Track service availability
- **Latency SLO**: Track p50, p95, p99 latency
- **Error Rate SLO**: Track error rates
- **Quota SLO**: Track quota utilization

#### 4.3 Configuration
```python
# forge/core/config/forge_config.py
alerting_enabled: bool = Field(
    default=False,
    description="Enable alerting policies"
)
alerting_endpoint: str | None = Field(
    default=None,
    description="Alerting endpoint (e.g., PagerDuty, Slack)"
)
alerting_api_key: SecretStr | None = Field(
    default=None,
    description="API key for alerting service"
)
slo_availability_target: float = Field(
    default=0.99,
    ge=0.0,
    le=1.0,
    description="Availability SLO target (0.0 to 1.0)"
)
slo_latency_p95_target_ms: float = Field(
    default=1000.0,
    description="P95 latency SLO target in milliseconds"
)
slo_error_rate_target: float = Field(
    default=0.01,
    ge=0.0,
    le=1.0,
    description="Error rate SLO target (0.0 to 1.0)"
)
```

#### 4.4 Implementation
- Use Prometheus metrics for SLO tracking
- Implement alert policies with thresholds
- Add alerting integrations (PagerDuty, Slack, etc.)
- Add SLO dashboard and reporting

---

## 5. Retry Queue with Graceful Degradation

### Current State
- Tenacity retry with fixed limits
- No retry queue for failed operations
- No graceful degradation
- Abrupt user-facing errors on failure

### Enhancements

#### 5.1 Retry Queue
- **Persistent Queue**: Store failed operations in Redis/DB
- **Retry Scheduling**: Schedule retries with exponential backoff
- **Dead Letter Queue**: Store permanently failed operations
- **Queue Monitoring**: Monitor queue size and processing rate

#### 5.2 Graceful Degradation
- **Fallback Mechanisms**: Provide fallback responses on failure
- **User-Friendly Messages**: Return graceful error messages
- **Partial Results**: Return partial results when possible
- **Circuit Breaker Integration**: Integrate with circuit breaker

#### 5.3 Configuration
```python
# forge/core/config/forge_config.py
retry_queue_enabled: bool = Field(
    default=True,
    description="Enable retry queue for failed operations"
)
retry_queue_backend: str = Field(
    default="redis",
    description="Retry queue backend: 'redis', 'memory', 'database'"
)
retry_queue_max_size: int = Field(
    default=10000,
    description="Maximum retry queue size"
)
retry_queue_max_retries: int = Field(
    default=3,
    description="Maximum retries per operation"
)
retry_queue_retry_delay_seconds: float = Field(
    default=60.0,
    description="Initial retry delay in seconds"
)
retry_queue_max_delay_seconds: float = Field(
    default=3600.0,
    description="Maximum retry delay in seconds"
)
graceful_degradation_enabled: bool = Field(
    default=True,
    description="Enable graceful degradation on failures"
)
```

#### 5.4 Implementation
- Use Redis/Database for retry queue
- Implement retry scheduler with exponential backoff
- Add graceful error messages
- Integrate with circuit breaker
- Add queue monitoring and metrics

---

## Implementation Priority

### Phase 1: Critical (P0)
1. ✅ **Redis-Backed Quota Persistence** - Production blocker
2. ✅ **Structured Logging** - Operational visibility

### Phase 2: High Priority (P1)
3. ✅ **Distributed Tracing** - Production observability
4. ✅ **Alert Policies** - Production reliability

### Phase 3: Medium Priority (P2)
5. ✅ **Retry Queue** - Better UX
6. ✅ **Graceful Degradation** - Better error handling

---

## Testing Strategy

### Unit Tests
- Redis quota persistence with fallback
- Structured logging with JSON format
- Tracing instrumentation
- Alert policies
- Retry queue operations

### Integration Tests
- End-to-end quota tracking with Redis
- Log shipping integration
- Tracing export
- Alert delivery
- Retry queue processing

### Performance Tests
- Redis connection pooling
- Log shipping overhead
- Tracing overhead
- Retry queue throughput

---

## Migration Path

### Step 1: Redis Quota (Week 1)
- Make Redis the default with graceful fallback
- Add connection pooling
- Add health checks
- Add metrics

### Step 2: Structured Logging (Week 2)
- Add JSON logging format
- Add structured fields
- Add log shipping support
- Add log rotation

### Step 3: Distributed Tracing (Week 3)
- Enable tracing by default
- Add exporters
- Add sampling
- Add context propagation

### Step 4: Alert Policies (Week 4)
- Add alert policies
- Add SLO tracking
- Add alerting integrations
- Add dashboards

### Step 5: Retry Queue (Week 5)
- Add retry queue
- Add graceful degradation
- Add circuit breaker integration
- Add monitoring

---

## Success Metrics

### Reliability
- **Availability**: 99.9% uptime
- **Error Rate**: < 1% error rate
- **Latency**: P95 < 1s

### Operations
- **Observability**: 100% request tracing
- **Alerting**: < 5 min alert response time
- **Logging**: 100% log coverage

### User Experience
- **Error Handling**: Graceful degradation
- **Retry Success**: > 90% retry success rate
- **User Feedback**: Clear error messages

---

## Next Steps

1. **Review and approve** this enhancement plan
2. **Prioritize** enhancements based on business needs
3. **Implement** Phase 1 (Redis Quota + Structured Logging)
4. **Test** and iterate
5. **Deploy** to production

---

## References

- [Redis Connection Pooling](https://redis.io/docs/manual/patterns/connection-pooling/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Structured Logging Best Practices](https://www.datadoghq.com/blog/json-logging/)
- [SLO Tracking with Prometheus](https://prometheus.io/docs/practices/alerting/)
