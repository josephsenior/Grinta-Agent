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
enable_metasop = true
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

### **MetaSOP Configuration**
```toml
[metasop]
# Enable MetaSOP
enable_metasop = true

# Agent settings
max_concurrent_agents = 5
agent_timeout = 300
retry_attempts = 3
retry_delay = 1.0

# Memory settings
enable_memory = true
memory_retention_days = 30
max_memory_size = 1000
memory_compression = true

# Monitoring
enable_monitoring = true
log_level = "INFO"
metrics_retention_days = 7

# ACE framework
enable_ace = true
ace_max_bullets = 1000
ace_similarity_threshold = 0.7
ace_max_refinement_rounds = 3
ace_multi_epoch = true
ace_num_epochs = 5

# Prompt optimization
enable_prompt_optimization = true
prompt_opt_ab_split = 0.1
prompt_opt_min_samples = 10
prompt_opt_confidence_threshold = 0.8
prompt_opt_success_weight = 0.4
prompt_opt_time_weight = 0.3
prompt_opt_error_weight = 0.2
prompt_opt_cost_weight = 0.1
prompt_opt_enable_evolution = true
prompt_opt_evolution_threshold = 0.05
prompt_opt_max_variants_per_prompt = 5
prompt_opt_storage_path = "data/prompt_optimization"
prompt_opt_sync_interval = 60
prompt_opt_auto_save = true
prompt_opt_history_path = "data/prompt_optimization/history.json"
prompt_opt_history_auto_flush = false
prompt_opt_history_path = "data/prompt_optimization/history.json"
prompt_opt_history_auto_flush = false
```

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

# Prompt optimization
enable_prompt_optimization = true
prompt_opt_storage_path = "data/prompt_optimization"
prompt_opt_ab_split = 0.1
prompt_opt_min_samples = 10
prompt_opt_confidence_threshold = 0.8
prompt_opt_success_weight = 0.4
prompt_opt_time_weight = 0.3
prompt_opt_error_weight = 0.2
prompt_opt_cost_weight = 0.1
prompt_opt_enable_evolution = true
prompt_opt_evolution_threshold = 0.05
prompt_opt_max_variants_per_prompt = 5
prompt_opt_sync_interval = 60
prompt_opt_auto_save = true

# Tool optimization
enable_tool_optimization = true
tool_opt_ab_split = 0.1
tool_opt_min_samples = 5
tool_opt_confidence_threshold = 0.7
tool_opt_success_weight = 0.4
tool_opt_time_weight = 0.3
tool_opt_error_weight = 0.2
tool_opt_cost_weight = 0.1
```

---

## ⚡ **Optimization Settings**

### **Prompt Optimization Configuration**
```toml
[prompt_optimization]
# Enable prompt optimization
enable = true

# Basic settings
ab_split = 0.1
min_samples = 10
confidence_threshold = 0.8
success_weight = 0.4
time_weight = 0.3
error_weight = 0.2
cost_weight = 0.1

# Evolution settings
enable_evolution = true
evolution_threshold = 0.05
max_variants_per_prompt = 5
evolution_frequency = 100

# Storage settings
storage_path = "data/prompt_optimization"
sync_interval = 60
auto_save = true
prompt_history_path = "data/prompt_optimization/history.json"
prompt_history_auto_flush = false
backup_enabled = true
backup_frequency = 24

# Advanced settings
enable_advanced_strategies = true
enable_multi_objective = true
enable_context_aware = true
enable_hierarchical = true
enable_real_time = true
```

### **Real-Time Optimization Configuration**
```toml
[real_time_optimization]
# Enable real-time optimization
enable = true

# Live optimizer settings
max_concurrent_optimizations = 5
optimization_threshold = 0.05
confidence_threshold = 0.8
retry_attempts = 3
retry_delay = 1.0

# Hot swapper settings
max_concurrent_swaps = 3
default_strategy = "atomic"
health_check_timeout = 5.0
rollback_timeout = 10.0

# Performance predictor settings
model_type = "ensemble"
retrain_frequency = 100
confidence_threshold = 0.7
prediction_cache_size = 1000

# Streaming engine settings
max_queue_size = 10000
processing_batch_size = 100
processing_interval = 0.1
anomaly_threshold = 2.0
pattern_window_size = 100

# Real-time monitor settings
update_interval = 1.0
max_history_size = 10000
trend_window_size = 100
alert_retention_days = 7

# WebSocket server settings
host = "localhost"
port = 8765
heartbeat_interval = 30.0
max_clients = 100
```

### **Advanced Optimization Strategies**
```toml
[advanced_optimization]
# Multi-objective optimization
enable_multi_objective = true
strategy_type = "balanced"  # balanced, performance_focused, cost_focused
pareto_frontier_size = 10
exploration_rate = 0.1
exploitation_rate = 0.9

# Context-aware optimization
enable_context_aware = true
context_analysis_depth = "deep"
similarity_threshold = 0.8
context_window_size = 1000
pattern_recognition = true

# Hierarchical optimization
enable_hierarchical = true
optimization_levels = ["system", "role", "tool"]
conflict_resolution = "priority_based"
synergy_detection = true
global_coordination = true

# Ensemble methods
enable_ensemble = true
ensemble_models = ["random_forest", "gradient_boosting", "linear_regression"]
ensemble_weights = [0.4, 0.4, 0.2]
confidence_threshold = 0.7
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

### **ACE Framework Configuration**
```toml
[ace]
# Enable ACE framework
enable_ace = true

# Context playbook settings
max_bullets = 1000
max_bullet_length = 500
similarity_threshold = 0.7

# Generator settings
max_trajectory_length = 2000
feedback_collection_enabled = true
multi_epoch_enabled = true
num_epochs = 5

# Reflector settings
max_refinement_rounds = 3
insight_quality_threshold = 0.6
pattern_detection_enabled = true

# Curator settings
deduplication_enabled = true
merge_similar_bullets = true
section_organization = true
tag_management = true

# Advanced settings
enable_multi_epoch = true
epoch_learning_rate = 0.1
epoch_memory_decay = 0.9
enable_context_evolution = true
evolution_threshold = 0.05
evolution_frequency = 100
enable_performance_tracking = true
track_insight_quality = true
track_context_effectiveness = true
context_retention_days = 30
max_context_size = 10000
compression_enabled = true
```

---

## 🔧 **Tool Settings**

### **Tool Integration Configuration**
```toml
[tool_integration]
# Enable tool integration
enable_tool_integration = true

# Tool optimizer settings
enable_tool_optimization = true
tool_opt_ab_split = 0.1
tool_opt_min_samples = 5
tool_opt_confidence_threshold = 0.7
tool_opt_success_weight = 0.4
tool_opt_time_weight = 0.3
tool_opt_error_weight = 0.2
tool_opt_cost_weight = 0.1

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
# MetaSOP
FORGE_METASOP_ENABLED=true
FORGE_METASOP_MAX_CONCURRENT_AGENTS=5
FORGE_METASOP_AGENT_TIMEOUT=300

# CodeAct
FORGE_CODEACT_ENABLED=true
FORGE_CODEACT_MAX_ITERATIONS=10
FORGE_CODEACT_TIMEOUT=300

# ACE Framework
FORGE_ACE_ENABLED=true
FORGE_ACE_MAX_BULLETS=1000
FORGE_ACE_SIMILARITY_THRESHOLD=0.7

# Tool Integration
FORGE_TOOL_INTEGRATION_ENABLED=true
FORGE_TOOL_OPTIMIZATION_ENABLED=true
FORGE_TOOL_OPTIMIZATION_AB_SPLIT=0.1

# WebSocket
FORGE_WEBSOCKET_ENABLED=true
FORGE_WEBSOCKET_PORT=8001
FORGE_WEBSOCKET_MAX_CONNECTIONS=500

# MetaSOP Services
FORGE_EVENT_SERVICE_GRPC=false
FORGE_RUNTIME_SERVICE_GRPC=false
FORGE_EVENT_SERVICE_ENDPOINT=
FORGE_RUNTIME_SERVICE_ENDPOINT=
```

Enable the gRPC adapters by setting `FORGE_EVENT_SERVICE_GRPC` and `FORGE_RUNTIME_SERVICE_GRPC` to `true` and
provide the corresponding `FORGE_EVENT_SERVICE_ENDPOINT` / `FORGE_RUNTIME_SERVICE_ENDPOINT` values (e.g.,
`event-service:50051`). Leave the flags `false` to continue using the in-process adapters.

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
