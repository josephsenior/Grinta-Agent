# 🤖 **Agent Configuration**

> **Configure CodeAct agent and agent behavior settings**

---

## 📖 **Table of Contents**

- [CodeAct Agent Configuration](#codeact-agent-configuration)
- [Timeout and Retry Settings](#timeout-and-retry-settings)
- [Memory Management](#memory-management)
- [Performance Tuning](#performance-tuning)

---

## 💻 **CodeAct Agent Configuration**

### **Basic Settings**

```toml
# config.toml
[codeact]
# Agent behavior
max_iterations = 30
enable_think_tool = true
enable_bash_tool = true
enable_editor_tool = true

# Code execution
sandbox_enabled = true
execution_timeout = 60  # seconds
```

### **Tool Configuration**

```toml
[codeact.tools]
# Available tools
bash = true
editor = true
browser = true
github = true
file_system = true

# Tool-specific settings
[codeact.tools.bash]
max_output_length = 10000
allowed_commands = ["ls", "cat", "grep", "find", "git"]

[codeact.tools.editor]
max_file_size_mb = 10
supported_languages = ["python", "typescript", "javascript", "java"]
```

---

## ⏱️ **Timeout and Retry Settings**

### **Global Timeouts**

```toml
[agents.timeouts]
# Maximum time for any single agent action
action_timeout_seconds = 120

# Maximum time for entire task
task_timeout_seconds = 1800  # 30 minutes

# Idle timeout (no progress)
idle_timeout_seconds = 300
```

### **Retry Configuration**

```toml
[agents.retry]
# Maximum retry attempts
max_retries = 3

# Retry delay (exponential backoff)
initial_delay_seconds = 5
max_delay_seconds = 60
backoff_multiplier = 2.0

# Retry on specific errors
retry_on_timeout = true
retry_on_rate_limit = true
retry_on_api_error = true
```

### **Error Handling**

```toml
[agents.error_handling]
# Continue on non-critical errors
continue_on_error = false

# Fallback to simpler model on failure
enable_model_fallback = true
fallback_model = "gpt-3.5-turbo"

# Save partial results on failure
save_partial_results = true
```

---

## 🔧 **Advanced Configuration**

### **Memory Management**

```toml
[agents.memory]
# Maximum conversation history length
max_history_length = 50

# Context window management
context_window_tokens = 16000
context_truncation_strategy = "smart"  # or "fifo", "summary"

# Memory persistence
persist_memory = true
memory_database = "sqlite:///./agent_memory.db"
```

### **Performance Tuning**

```toml
[agents.performance]
# Streaming responses
enable_streaming = true

# Parallel tool execution
parallel_tools = true
max_parallel_tools = 3

# Caching
cache_enabled = true
cache_ttl_seconds = 3600
```

---

## 🎯 **Configuration Best Practices**

### **1. Environment-Specific Configs**

```bash
# Development
config.dev.toml → Fast, less thorough

# Production
config.prod.toml → Slower, more thorough, higher quality
```

### **2. Performance vs Quality Trade-offs**

**Fast Mode (Development):**
- Lower max_tokens (2000-3000)
- Fewer retries (1-2)
- Shorter timeouts (60-120s)
- Parallel execution enabled

**Quality Mode (Production):**
- Higher max_tokens (4000-8000)
- More retries (3-5)
- Longer timeouts (300-600s)
- Sequential execution for critical tasks

---

## 📚 **Related Documentation**

- [System Configuration](system-config.md)
- [Optimization Configuration](optimization-config.md)
- [CodeAct Agent](../features/codeact-agent.md)

---

**Remember:** Agent configuration significantly impacts performance, cost, and quality. Choose settings appropriate for your use case!
