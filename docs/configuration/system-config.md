# ⚙️ **System Configuration**

> **Comprehensive configuration guide for the Forge platform, covering all components and advanced settings.**

---

## 📖 **Table of Contents**

- [🌟 Overview](#-overview)
- [🏗️ Configuration Structure](#️-configuration-structure)
- [🔧 Core Settings](#-core-settings)
- [🤖 Agent Configuration](#-agent-configuration)
- [⚡ Optimization Settings](#-optimization-settings)
- [💾 Memory Settings](#-memory-settings)
- [🔧 Tool Settings](#-tool-settings)
- [📊 Monitoring Settings](#-monitoring-settings)
- [🚀 Advanced Settings](#-advanced-settings)
- [🎯 Environment Variables](#-environment-variables)
- [🔍 Troubleshooting](#-troubleshooting)

---

## 🌟 **Overview**

The Forge platform uses a comprehensive configuration system that allows fine-tuning of all components. Configuration is managed through TOML files, environment variables, and runtime settings.

### **Configuration Sources**
1. **Default Configuration**: Built-in defaults
2. **Configuration Files**: TOML files for different environments
3. **Environment Variables**: Runtime overrides
4. **Runtime Settings**: Dynamic configuration updates

### **Configuration Hierarchy**
```
Runtime Settings (highest priority)
    ↓
Environment Variables
    ↓
Configuration Files
    ↓
Default Configuration (lowest priority)
```

---

## 🏗️ **Configuration Structure**

### **Main Configuration File**
```toml
# config.toml - Main configuration file
[system]
name = "Forge"
version = "2.2.0"
environment = "development"
debug = false

[logging]
level = "INFO"
format = "json"
file = "logs/Forge.log"
max_size = "100MB"
backup_count = 5

[server]
host = "localhost"
port = 8000
workers = 4
timeout = 30
max_connections = 1000

[database]
url = "sqlite:///Forge.db"
pool_size = 10
max_overflow = 20
echo = false

[llm]
provider = "openai"
model = "gpt-4"
temperature = 0.1
max_tokens = 4000
timeout = 60
```

### **Environment-Specific Configuration**
```toml
# config.production.toml - Production configuration
[system]
environment = "production"
debug = false

[logging]
level = "WARNING"
file = "/var/log/Forge/app.log"

[server]
host = "0.0.0.0"
port = 8000
workers = 8

[database]
url = "postgresql://user:pass@localhost/Forge"
pool_size = 20
max_overflow = 40

[llm]
provider = "openai"
model = "gpt-4"
temperature = 0.1
```

---

## 🔧 **Core Settings**

### **System Configuration**
```toml
[system]
# Basic system settings
name = "Forge"
version = "2.2.0"
environment = "development"  # development, staging, production
debug = false
log_level = "INFO"

# Performance settings
max_workers = 4
worker_timeout = 300
memory_limit = "2GB"
cpu_limit = "80%"

# Security settings
enable_cors = true
cors_origins = ["http://localhost:3000", "https://app.Forge.ai"]
enable_rate_limiting = true
rate_limit_requests = 100
rate_limit_window = 60

# Feature flags
enable_codeact = true
enable_memory = true
enable_optimization = true
enable_monitoring = true
```

### **Server Configuration**
```toml
[server]
# Basic server settings
host = "localhost"
port = 8000
workers = 4
timeout = 30
keep_alive = 2

# Connection settings
max_connections = 1000
max_keep_alive_connections = 100
connection_timeout = 30
read_timeout = 30
write_timeout = 30

# SSL settings (for production)
ssl_enabled = false
ssl_cert_file = ""
ssl_key_file = ""

# WebSocket settings
websocket_enabled = true
websocket_port = 8001
websocket_max_connections = 500
websocket_ping_interval = 30
websocket_ping_timeout = 10
```

### **Database Configuration**
```toml
[database]
# Database connection
url = "sqlite:///Forge.db"
# For PostgreSQL: "postgresql://user:pass@localhost/Forge"
# For MySQL: "mysql://user:pass@localhost/Forge"

# Connection pool settings
pool_size = 10
max_overflow = 20
pool_timeout = 30
pool_recycle = 3600
pool_pre_ping = true

# Database options
echo = false
echo_pool = false
future = true

# Migration settings
migration_dir = "migrations"
auto_migrate = true
backup_before_migrate = true
```

---

## 🤖 **Agent Configuration**

### **CodeAct Agent Configuration**
```toml
[codeact]
# Enable CodeAct agent
enable_codeact = true

# Agent settings
name = "CodeActAgent"
description = "Minimalist agent for code generation"
max_iterations = 10
timeout = 300

# LLM settings
llm_provider = "openai"
llm_model = "gpt-4"
llm_temperature = 0.1
llm_max_tokens = 4000
llm_timeout = 60

# Memory settings
enable_memory = true
memory_retention_days = 30
max_memory_size = 1000
memory_compression = true
```

---

## 💾 **Memory Settings**

### **Memory System Configuration**
```toml
[memory]
# Enable memory system
enable_memory = true

# Conversation memory settings
max_conversations = 1000
max_conversation_length = 10000
conversation_retention_days = 30
enable_compression = true

# Context condenser settings
compression_ratio = 0.5
quality_threshold = 0.8
preserve_key_info = true
max_compression_cycles = 3

# Memory indexing settings
vector_dimension = 768
max_vectors = 10000
similarity_threshold = 0.7
enable_lexical_search = true
enable_hybrid_search = true

# Context evolution settings
enable_evolution = true
evolution_threshold = 0.05
learning_rate = 0.1
max_evolution_cycles = 100

# Performance optimization
enable_caching = true
cache_size = 1000
cache_ttl = 3600

# Memory management
enable_auto_cleanup = true
cleanup_frequency = 24
cleanup_threshold = 0.8

# Monitoring
enable_detailed_monitoring = true
track_search_accuracy = true
track_compression_efficiency = true
track_evolution_effectiveness = true
```

---

## 🔧 **Tool Settings**

### **Tool Integration Configuration**
```toml
[tool_integration]
# Enable tool integration
enable_tool_integration = true

# Function calling settings
enable_function_calling = true
max_concurrent_calls = 10
call_timeout = 30
enable_parameter_validation = true

# Tool registry settings
enable_tool_registry = true
auto_discover_tools = true
tool_versioning = true
dependency_tracking = true

# Performance tracking
enable_performance_tracking = true
track_usage_statistics = true
track_performance_metrics = true
track_cost_analysis = true

# Error recovery
enable_error_recovery = true
max_retries = 3
retry_delay = 1.0
circuit_breaker_threshold = 5
fallback_strategies = ["alternative_tool", "simplified_parameters"]

# Advanced optimization
enable_advanced_optimization = true
optimization_frequency = 100
adaptive_learning = true
context_aware_optimization = true

# Monitoring and alerting
enable_monitoring = true
alert_thresholds = {
    success_rate = 0.8,
    execution_time = 10.0,
    error_rate = 0.2
}
log_level = "INFO"
```

### **Tool-Specific Configuration**
```toml
[tools.think]
enabled = true
max_steps = 10
reasoning_depth = "deep"
confidence_threshold = 0.7
optimization_enabled = true

[tools.bash]
enabled = true
timeout = 30
allowed_commands = ["ls", "cd", "mkdir", "git", "npm", "pip"]
blocked_commands = ["rm", "del", "format", "shutdown"]
sandbox_mode = true

[tools.python]
enabled = true
timeout = 60
max_execution_time = 30
allowed_modules = ["os", "sys", "json", "requests", "pandas"]
blocked_modules = ["subprocess", "os.system", "eval"]
sandbox_mode = true

[tools.git]
enabled = true
timeout = 60
allowed_commands = ["status", "add", "commit", "push", "pull", "clone"]
blocked_commands = ["reset", "rebase", "merge"]
safe_mode = true
```

---

## 📊 **Monitoring Settings**

### **Monitoring Configuration**
```toml
[monitoring]
# Enable monitoring
enable_monitoring = true

# Basic monitoring
log_level = "INFO"
metrics_enabled = true
health_checks_enabled = true
performance_tracking = true

# Metrics settings
metrics_retention_days = 7
metrics_aggregation_interval = 60
metrics_export_enabled = true
metrics_export_format = "prometheus"

# Health checks
health_check_interval = 30
health_check_timeout = 5
health_check_retries = 3

# Alerting
alerts_enabled = true
alert_channels = ["email", "webhook", "slack"]
alert_thresholds = {
    cpu_usage = 80.0,
    memory_usage = 80.0,
    disk_usage = 90.0,
    error_rate = 5.0,
    response_time = 5.0
}

# Dashboard
dashboard_enabled = true
dashboard_port = 3001
dashboard_theme = "dark"
real_time_updates = true
```

### **Analytics Configuration**
```toml
[analytics]
# Enable analytics
enable_analytics = true

# Data collection
collect_usage_data = true
collect_performance_data = true
collect_error_data = true
collect_user_behavior = true

# Data retention
retention_days = 30
aggregation_enabled = true
aggregation_interval = 3600

# Privacy
anonymize_data = true
data_encryption = true
gdpr_compliance = true

# Export
export_enabled = true
export_format = "json"
export_frequency = "daily"
export_destination = "s3://analytics-bucket"
```

---

## 🚀 **Advanced Settings**

### **Performance Configuration**
```toml
[performance]
# CPU settings
max_cpu_usage = 80.0
cpu_affinity = [0, 1, 2, 3]
cpu_priority = "normal"

# Memory settings
max_memory_usage = 80.0
memory_cleanup_interval = 300
memory_compression = true

# I/O settings
max_io_operations = 1000
io_timeout = 30
io_retry_attempts = 3

# Network settings
max_network_connections = 1000
network_timeout = 30
network_retry_attempts = 3
keep_alive = true
```

### **Security Configuration**
```toml
[security]
# Authentication
enable_authentication = true
auth_provider = "jwt"
jwt_secret = "your-secret-key"
jwt_expiry = 3600
refresh_token_expiry = 86400

# Authorization
enable_authorization = true
role_based_access = true
permission_model = "rbac"

# Encryption
enable_encryption = true
encryption_algorithm = "AES-256-GCM"
key_rotation_interval = 86400

# Rate limiting
enable_rate_limiting = true
rate_limit_requests = 100
rate_limit_window = 60
rate_limit_strategy = "sliding_window"

# CORS
enable_cors = true
cors_origins = ["http://localhost:3000", "https://app.Forge.ai"]
cors_methods = ["GET", "POST", "PUT", "DELETE"]
cors_headers = ["Content-Type", "Authorization"]
```

### **Caching Configuration**
```toml
[caching]
# Enable caching
enable_caching = true

# Cache backends
default_backend = "redis"
redis_url = "redis://localhost:6379/0"
redis_max_connections = 100
redis_timeout = 5

# Cache settings
default_ttl = 3600
max_cache_size = "1GB"
cache_eviction_policy = "lru"

# Cache keys
key_prefix = "Forge:"
key_separator = ":"
key_encoding = "utf-8"

# Cache warming
enable_cache_warming = true
warmup_interval = 300
warmup_batch_size = 100
```

---

## 🎯 **Environment Variables**

### **Core Environment Variables**
```bash
# System settings
FORGE_ENVIRONMENT=development
FORGE_DEBUG=false
FORGE_LOG_LEVEL=INFO

# Server settings
FORGE_HOST=localhost
FORGE_PORT=8000
FORGE_WORKERS=4

# Database settings
FORGE_DATABASE_URL=sqlite:///Forge.db
FORGE_DATABASE_POOL_SIZE=10

# LLM settings
FORGE_LLM_PROVIDER=openai
FORGE_LLM_MODEL=gpt-4
FORGE_LLM_API_KEY=your-api-key
FORGE_LLM_TEMPERATURE=0.1
FORGE_LLM_MAX_TOKENS=4000

# Memory settings
FORGE_MEMORY_ENABLED=true
FORGE_MEMORY_MAX_CONVERSATIONS=1000
FORGE_MEMORY_RETENTION_DAYS=30

# Optimization settings
FORGE_OPTIMIZATION_ENABLED=true
FORGE_OPTIMIZATION_AB_SPLIT=0.1
FORGE_OPTIMIZATION_MIN_SAMPLES=10
FORGE_OPTIMIZATION_CONFIDENCE_THRESHOLD=0.8

# Real-time optimization
FORGE_REAL_TIME_OPTIMIZATION_ENABLED=true
FORGE_REAL_TIME_OPTIMIZATION_THRESHOLD=0.05
FORGE_REAL_TIME_OPTIMIZATION_CONFIDENCE_THRESHOLD=0.8

# Monitoring
FORGE_MONITORING_ENABLED=true
FORGE_MONITORING_LOG_LEVEL=INFO
FORGE_MONITORING_METRICS_ENABLED=true
```

### **Feature-Specific Environment Variables**
```bash
# CodeAct
FORGE_CODEACT_ENABLED=true
FORGE_CODEACT_MAX_ITERATIONS=10
FORGE_CODEACT_TIMEOUT=300

# Tool Integration
FORGE_TOOL_INTEGRATION_ENABLED=true
FORGE_TOOL_OPTIMIZATION_ENABLED=true
FORGE_TOOL_OPTIMIZATION_AB_SPLIT=0.1

# WebSocket
FORGE_WEBSOCKET_ENABLED=true
FORGE_WEBSOCKET_PORT=8001
FORGE_WEBSOCKET_MAX_CONNECTIONS=500
```

---

## 🔍 **Troubleshooting**

### **Common Configuration Issues**

#### **Configuration Not Loading**
```bash
# Check configuration file syntax
toml validate config.toml

# Check environment variables
env | grep Forge

# Check configuration loading
python -c "from forge.core.config import load_config; print(load_config())"
```

#### **Feature Not Working**
```bash
# Check feature flags
grep -r "enable_" config.toml

# Check environment variables
env | grep FORGE_.*_ENABLED

# Check runtime configuration
curl http://localhost:3000/api/options/config
```

#### **Performance Issues**
```bash
# Check resource limits
grep -r "max_\|limit" config.toml

# Check monitoring
curl http://localhost:3000/api/monitoring/metrics

# Check logs
tail -f logs/Forge.log
```

### **Configuration Validation**

#### **Validate Configuration**
```python
from forge.core.config import validate_config

# Validate configuration
validation_result = validate_config("config.toml")
if validation_result.valid:
    print("Configuration is valid")
else:
    print(f"Configuration errors: {validation_result.errors}")
```

#### **Check Configuration Status**
```python
from forge.core.config import get_config_status

# Get configuration status
status = get_config_status()
print(f"Configuration loaded: {status['loaded']}")
print(f"Features enabled: {status['features']}")
print(f"Warnings: {status['warnings']}")
```

---

## 📈 **Best Practices**

### **Configuration Management**
1. **Use Environment-Specific Files**: Separate configs for dev/staging/prod
2. **Use Environment Variables**: Override sensitive settings
3. **Validate Configuration**: Always validate before deployment
4. **Document Settings**: Document all configuration options

### **Performance Tuning**
1. **Start Conservative**: Begin with conservative settings
2. **Monitor Performance**: Track metrics and adjust accordingly
3. **Tune Gradually**: Make incremental changes
4. **Test Changes**: Test configuration changes thoroughly

### **Security**
1. **Use Secrets Management**: Store sensitive data securely
2. **Enable Security Features**: Use authentication, authorization, encryption
3. **Regular Updates**: Keep configuration up to date
4. **Audit Configuration**: Regularly audit configuration settings

---

**System Configuration - The foundation of Forge platform.** ⚙️
