# ⚡ **Optimization Configuration**

> **Configure dynamic prompt optimization, A/B testing, and real-time adaptation settings**

---

## 📖 **Table of Contents**

- [Enable Optimization](#enable-optimization)
- [A/B Testing Configuration](#ab-testing-configuration)
- [Real-Time Optimization](#real-time-optimization)
- [Performance Tracking](#performance-tracking)
- [Advanced Settings](#advanced-settings)

---

## 🎯 **Enable Optimization**

### **Basic Configuration**

```toml
# config.toml
[optimization]
# Enable dynamic prompt optimization
enabled = true

# Optimization strategy
strategy = "multi_objective"  # or "success_rate", "speed", "cost"

# Update frequency
check_interval_seconds = 60
```

### **Environment Variables**

```bash
# .env
OPENHANDS_ENABLE_PROMPT_OPTIMIZATION=true
OPENHANDS_OPTIMIZATION_STRATEGY=multi_objective
```

---

## 🧪 **A/B Testing Configuration**

### **Test Settings**

```toml
[optimization.ab_testing]
# Enable A/B testing
enabled = true

# Traffic split (0.0 to 1.0)
# 0.2 = 20% gets variant B, 80% gets variant A
split_ratio = 0.2

# Minimum samples before statistical analysis
min_samples_per_variant = 50

# Statistical confidence threshold
confidence_threshold = 0.95  # 95% confidence
```

### **Variant Management**

```toml
[optimization.variants]
# Maximum variants per prompt
max_variants = 5

# Automatically generate new variants
auto_generate_variants = true

# Variant generation strategy
generation_strategy = "llm_evolution"  # or "manual", "template"

# Variant lifetime
variant_ttl_days = 30  # Remove old variants
```

---

## 🔄 **Real-Time Optimization**

### **Hot-Swapping**

```toml
[optimization.hot_swapping]
# Enable zero-downtime updates
enabled = true

# Automatic best variant activation
auto_activate_best = true

# Staged rollout
staged_rollout = true
rollout_percentage_step = 20  # 20%, 40%, 60%, 80%, 100%
rollout_interval_minutes = 30

# Automatic rollback on performance drop
auto_rollback = true
rollback_threshold = 0.1  # Rollback if 10% worse
```

### **Adaptation Settings**

```toml
[optimization.adaptation]
# Adaptation frequency
adaptation_interval_seconds = 300  # 5 minutes

# Performance improvement threshold
improvement_threshold = 0.05  # 5% improvement to trigger update

# Adaptation strategies
strategies = [
    "multi_objective",
    "context_aware",
    "hierarchical"
]
```

---

## 📊 **Performance Tracking**

### **Metrics Configuration**

```toml
[optimization.metrics]
# Tracked metrics
track_success_rate = true
track_execution_time = true
track_token_usage = true
track_cost = true
track_user_satisfaction = true

# Metric weights for multi-objective optimization
[optimization.metrics.weights]
success_rate = 0.4
execution_time = 0.2
token_usage = 0.2
cost = 0.1
user_satisfaction = 0.1
```

### **Performance Targets**

```toml
[optimization.targets]
# Target thresholds
min_success_rate = 0.85  # 85%
max_execution_time_seconds = 30
max_tokens_per_request = 4000
max_cost_per_request = 0.50  # USD
min_user_satisfaction = 4.0  # 1-5 scale
```

---

## 🔧 **Advanced Settings**

### **ML Prediction**

```toml
[optimization.ml_prediction]
# Enable ML-powered performance forecasting
enabled = true

# Models to use
models = ["random_forest", "xgboost", "neural_network"]

# Model training
retrain_interval_hours = 24
min_training_samples = 1000

# Confidence scoring
min_prediction_confidence = 0.7
```

### **Context-Aware Optimization**

```toml
[optimization.context_aware]
# Enable context-based prompt selection
enabled = true

# Context features to consider
features = [
    "task_complexity",
    "task_type",
    "user_expertise",
    "time_of_day",
    "system_load"
]

# Context similarity threshold
similarity_threshold = 0.8
```

---

## 💾 **Storage Configuration**

### **Optimization Data Storage**

```toml
[optimization.storage]
# Storage backend
backend = "hybrid"  # or "local", "central"

# Local cache
local_cache_enabled = true
local_cache_size_mb = 100
local_cache_ttl_seconds = 3600

# Central storage
central_storage_url = "redis://localhost:6379"
sync_interval_seconds = 300
```

### **Data Retention**

```toml
[optimization.retention]
# How long to keep optimization data
performance_data_days = 90
variant_history_days = 180
ab_test_results_days = 365

# Data cleanup schedule
cleanup_interval_hours = 24
```

---

## 🚨 **Alert Configuration**

### **Performance Alerts**

```toml
[optimization.alerts]
# Enable alerting
enabled = true

# Alert thresholds
[optimization.alerts.thresholds]
success_rate_drop = 0.1  # Alert if drops 10%
latency_increase = 0.5   # Alert if increases 50%
cost_increase = 0.3      # Alert if increases 30%

# Alert channels
channels = ["log", "email", "webhook"]

# Alert configuration
[optimization.alerts.email]
smtp_host = "smtp.gmail.com"
smtp_port = 587
recipients = ["admin@example.com"]

[optimization.alerts.webhook]
url = "https://hooks.slack.com/services/..."
```

---

## 📝 **Configuration Examples**

### **Example 1: Aggressive Optimization**

```toml
# Fast iteration, frequent updates
[optimization]
enabled = true
strategy = "multi_objective"
check_interval_seconds = 30

[optimization.ab_testing]
enabled = true
split_ratio = 0.3  # 30% variant traffic
min_samples_per_variant = 30
confidence_threshold = 0.90

[optimization.hot_swapping]
enabled = true
auto_activate_best = true
staged_rollout = false  # Immediate rollout
auto_rollback = true
```

### **Example 2: Conservative Optimization**

```toml
# Careful testing, slow rollout
[optimization]
enabled = true
strategy = "multi_objective"
check_interval_seconds = 300

[optimization.ab_testing]
enabled = true
split_ratio = 0.1  # Only 10% variant traffic
min_samples_per_variant = 100
confidence_threshold = 0.99  # Very high confidence

[optimization.hot_swapping]
enabled = true
auto_activate_best = false  # Manual approval
staged_rollout = true
rollout_percentage_step = 10  # Slow rollout
rollout_interval_minutes = 60
```

### **Example 3: Development Mode**

```toml
# Fast iteration during development
[optimization]
enabled = true
strategy = "success_rate"  # Simple strategy
check_interval_seconds = 60

[optimization.ab_testing]
enabled = true
split_ratio = 0.5  # Equal split
min_samples_per_variant = 10  # Low threshold
confidence_threshold = 0.80

[optimization.hot_swapping]
enabled = true
auto_activate_best = true
staged_rollout = false
auto_rollback = false  # Manual rollback
```

---

## 🎯 **Optimization Strategies**

### **1. Success Rate Optimization**

```toml
[optimization]
strategy = "success_rate"

# Focus on maximizing task completion rate
# Best for: Mission-critical tasks
```

### **2. Speed Optimization**

```toml
[optimization]
strategy = "speed"

# Focus on minimizing execution time
# Best for: Real-time applications
```

### **3. Cost Optimization**

```toml
[optimization]
strategy = "cost"

# Focus on minimizing API costs
# Best for: High-volume, budget-constrained scenarios
```

### **4. Multi-Objective Optimization**

```toml
[optimization]
strategy = "multi_objective"

[optimization.metrics.weights]
success_rate = 0.4      # 40% weight
execution_time = 0.2    # 20% weight
token_usage = 0.2       # 20% weight
cost = 0.1              # 10% weight
user_satisfaction = 0.1 # 10% weight

# Balances multiple objectives
# Best for: Production environments
```

---

## 📊 **Monitoring Optimization**

### **Track Optimization Performance**

```bash
# View optimization metrics
curl http://localhost:8000/api/optimization/metrics

# View A/B test results
curl http://localhost:8000/api/optimization/ab-tests

# View best performing variants
curl http://localhost:8000/api/optimization/best-variants
```

### **Optimization Dashboard**

Access real-time optimization dashboard:
```
http://localhost:3000/optimization
```

---

## 📚 **Related Documentation**

- [Dynamic Prompt Optimization](../features/prompt-optimization.md)
- [Real-Time Optimization](../features/real-time-optimization.md)
- [Performance Prediction](../features/performance-prediction.md)
- [Hot-Swapping](../features/hot-swapping.md)

---

**Remember:** Optimization settings should be adjusted based on your specific use case, traffic patterns, and quality requirements!

