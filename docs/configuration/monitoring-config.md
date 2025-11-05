# 📊 **Monitoring Configuration**

> **Configure logging, metrics, dashboards, and alerting for OpenHands**

---

## 📖 **Table of Contents**

- [Logging Configuration](#logging-configuration)
- [Metrics Collection](#metrics-collection)
- [Dashboard Settings](#dashboard-settings)
- [Alerting Configuration](#alerting-configuration)
- [External Integrations](#external-integrations)

---

## 📝 **Logging Configuration**

### **Basic Logging**

```toml
# config.toml
[logging]
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
level = "INFO"

# Log format
format = "json"  # or "text"

# Log destination
output = ["console", "file"]

# File logging
[logging.file]
path = "./logs/openhands.log"
max_size_mb = 100
max_files = 10
rotation = "daily"  # or "size"
```

### **Environment Variables**

```bash
# .env
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_OUTPUT=console,file
```

### **Component-Specific Logging**

```toml
[logging.components]
# Override log levels for specific components
agents = "DEBUG"
optimization = "INFO"
websocket = "WARNING"
database = "ERROR"
```

---

## 📊 **Metrics Collection**

### **Enable Metrics**

```toml
[monitoring.metrics]
# Enable metrics collection
enabled = true

# Metrics backend
backend = "prometheus"  # or "statsd", "datadog"

# Collection interval
interval_seconds = 60

# Metrics to collect
[monitoring.metrics.collect]
system_metrics = true    # CPU, memory, disk
agent_metrics = true     # Agent performance
optimization_metrics = true  # Prompt optimization
api_metrics = true       # API latency, throughput
websocket_metrics = true # WebSocket connections
```

### **Prometheus Configuration**

```toml
[monitoring.prometheus]
enabled = true
port = 9090
endpoint = "/metrics"

# Metric prefixes
prefix = "openhands_"

# Additional labels
[monitoring.prometheus.labels]
environment = "production"
region = "us-west-2"
```

---

## 🎨 **Dashboard Settings**

### **Built-in Dashboard**

```toml
[monitoring.dashboard]
# Enable built-in dashboard
enabled = true

# Dashboard port
port = 3001

# Dashboard route
route = "/monitoring"

# Real-time updates
websocket_enabled = true
update_interval_seconds = 5
```

### **Dashboard Features**

```toml
[monitoring.dashboard.features]
# Enable specific dashboard sections
system_overview = true
agent_performance = true
optimization_status = true
resource_usage = true
error_tracking = true
user_activity = true
```

### **Dashboard Customization**

```toml
[monitoring.dashboard.ui]
# Theme
theme = "dark"  # or "light", "system"

# Refresh rate
auto_refresh = true
refresh_interval_seconds = 10

# Time range presets
time_ranges = ["1h", "6h", "24h", "7d", "30d"]
default_time_range = "24h"
```

---

## 🚨 **Alerting Configuration**

### **Alert Rules**

```toml
[monitoring.alerts]
# Enable alerting
enabled = true

# Alert evaluation interval
evaluation_interval_seconds = 60

# Alert rules
[[monitoring.alerts.rules]]
name = "high_error_rate"
condition = "error_rate > 0.05"  # 5% error rate
severity = "critical"
for_duration_seconds = 300  # Must persist for 5 minutes

[[monitoring.alerts.rules]]
name = "high_latency"
condition = "p95_latency > 5000"  # 5 seconds
severity = "warning"
for_duration_seconds = 600

[[monitoring.alerts.rules]]
name = "high_memory_usage"
condition = "memory_usage_percent > 85"
severity = "warning"
for_duration_seconds = 300
```

### **Alert Channels**

```toml
[monitoring.alerts.channels]
# Console logging
console = true

# File logging
file = true
file_path = "./logs/alerts.log"

# Email notifications
[monitoring.alerts.email]
enabled = true
smtp_host = "smtp.gmail.com"
smtp_port = 587
username = "alerts@example.com"
password_env = "SMTP_PASSWORD"
recipients = ["admin@example.com", "ops@example.com"]

# Slack notifications
[monitoring.alerts.slack]
enabled = true
webhook_url_env = "SLACK_WEBHOOK_URL"
channel = "#openhands-alerts"
mention_on_critical = "@here"

# PagerDuty integration
[monitoring.alerts.pagerduty]
enabled = false
integration_key_env = "PAGERDUTY_KEY"
```

---

## 🔌 **External Integrations**

### **Sentry (Error Tracking)**

```toml
[monitoring.sentry]
enabled = true
dsn_env = "SENTRY_DSN"
environment = "production"
release = "1.0.0"

# Error sampling
sample_rate = 1.0  # 100% of errors

# Performance monitoring
traces_sample_rate = 0.1  # 10% of transactions
```

### **DataDog**

```toml
[monitoring.datadog]
enabled = false
api_key_env = "DATADOG_API_KEY"
app_key_env = "DATADOG_APP_KEY"
site = "datadoghq.com"

# Metrics
[monitoring.datadog.metrics]
flush_interval_seconds = 60

# Logs
[monitoring.datadog.logs]
enabled = true
source = "openhands"
```

### **Grafana**

```toml
[monitoring.grafana]
enabled = false
url = "http://localhost:3000"
api_key_env = "GRAFANA_API_KEY"

# Dashboard IDs
dashboards = [
    "openhands-overview",
    "agent-performance",
    "optimization-metrics"
]
```

### **New Relic**

```toml
[monitoring.newrelic]
enabled = false
license_key_env = "NEW_RELIC_LICENSE_KEY"
app_name = "OpenHands"

# Distributed tracing
distributed_tracing = true
```

---

## 📈 **Performance Tracking**

### **Agent Performance**

```toml
[monitoring.agent_performance]
# Track agent metrics
track_execution_time = true
track_success_rate = true
track_token_usage = true
track_error_rate = true

# Percentiles to calculate
percentiles = [50, 90, 95, 99]

# Breakdown by
dimensions = ["agent_type", "task_type", "model"]
```

### **API Performance**

```toml
[monitoring.api_performance]
# Track API metrics
track_request_count = true
track_response_time = true
track_error_rate = true
track_throughput = true

# Request/response logging
log_requests = false  # Can be verbose
log_responses = false
log_errors = true
```

---

## 🗄️ **Data Retention**

### **Metrics Retention**

```toml
[monitoring.retention]
# How long to keep metrics data
raw_metrics_days = 7
aggregated_metrics_days = 90
alert_history_days = 365

# Automatic cleanup
auto_cleanup = true
cleanup_interval_hours = 24
```

### **Logs Retention**

```toml
[monitoring.retention.logs]
# Log retention periods
debug_logs_days = 1
info_logs_days = 7
warning_logs_days = 30
error_logs_days = 90
critical_logs_days = 365
```

---

## 📝 **Configuration Examples**

### **Example 1: Development Environment**

```toml
# Verbose logging, minimal external integrations
[logging]
level = "DEBUG"
format = "text"
output = ["console"]

[monitoring.metrics]
enabled = true
backend = "prometheus"

[monitoring.dashboard]
enabled = true
port = 3001

[monitoring.alerts]
enabled = false  # No alerts in dev
```

### **Example 2: Production Environment**

```toml
# Structured logging, full monitoring stack
[logging]
level = "INFO"
format = "json"
output = ["console", "file"]

[monitoring.metrics]
enabled = true
backend = "prometheus"
interval_seconds = 30

[monitoring.dashboard]
enabled = true
port = 3001

[monitoring.alerts]
enabled = true
evaluation_interval_seconds = 60

[monitoring.sentry]
enabled = true
dsn_env = "SENTRY_DSN"

[monitoring.alerts.email]
enabled = true
recipients = ["ops@example.com"]

[monitoring.alerts.slack]
enabled = true
webhook_url_env = "SLACK_WEBHOOK_URL"
```

### **Example 3: Enterprise Setup**

```toml
# Complete monitoring with all integrations
[logging]
level = "INFO"
format = "json"
output = ["console", "file"]

[monitoring.metrics]
enabled = true
backend = "datadog"

[monitoring.datadog]
enabled = true
api_key_env = "DATADOG_API_KEY"

[monitoring.sentry]
enabled = true
dsn_env = "SENTRY_DSN"

[monitoring.grafana]
enabled = true
url = "https://grafana.company.com"

[monitoring.alerts]
enabled = true

[monitoring.alerts.pagerduty]
enabled = true
integration_key_env = "PAGERDUTY_KEY"
```

---

## 🎯 **Best Practices**

### **1. Structured Logging**

```python
# Use structured logging with context
logger.info(
    "Agent execution completed",
    extra={
        "agent_type": "product_manager",
        "duration_seconds": 15.3,
        "success": True,
        "tokens_used": 2500
    }
)
```

### **2. Metric Naming**

Follow naming conventions:
```
openhands_<component>_<metric_name>_<unit>

Examples:
- openhands_agent_execution_time_seconds
- openhands_api_requests_total
- openhands_optimization_success_rate
```

### **3. Alert Fatigue Prevention**

- Set appropriate thresholds
- Use `for_duration` to avoid transient alerts
- Group related alerts
- Set different severity levels

### **4. Dashboard Organization**

- **Overview Dashboard**: High-level health metrics
- **Component Dashboards**: Detailed metrics per component
- **Troubleshooting Dashboards**: For incident response

---

## 📚 **Related Documentation**

- [Live Monitoring](../features/live-monitoring.md)
- [Performance Tuning](../guides/performance-tuning.md)
- [Troubleshooting](../guides/troubleshooting.md)
- [System Configuration](system-config.md)

---

**Remember:** Good monitoring is essential for production systems. Start simple and expand as needs grow!

