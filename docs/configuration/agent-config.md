# 🤖 **Agent Configuration**

> **Configure MetaSOP agents, CodeAct agent, and agent behavior settings**

---

## 📖 **Table of Contents**

- [MetaSOP Agent Configuration](#metasop-agent-configuration)
- [CodeAct Agent Configuration](#codeact-agent-configuration)
- [Agent Profiles](#agent-profiles)
- [Timeout and Retry Settings](#timeout-and-retry-settings)
- [Examples](#examples)

---

## 🎯 **MetaSOP Agent Configuration**

### **Enable/Disable MetaSOP**

```toml
# config.toml
[metasop]
enabled = true
default_template = "full_stack_dev"
max_retries_per_step = 2
step_timeout_seconds = 300
```

### **Agent Selection**

```toml
[metasop.agents]
# Enable/disable specific agents
product_manager = true
architect = true
engineer = true
qa = true
ui_designer = true
devops = false  # Optional agent
```

### **Orchestration Settings**

```toml
[metasop.orchestration]
# Allow parallel execution of independent steps
parallel_execution = true

# Maximum concurrent agents
max_concurrent_agents = 3

# Auto-proceed to next step if validation passes
auto_proceed = false  # Requires manual approval

# Enable causal reasoning engine
causal_reasoning_enabled = true

# Enable predictive execution planning
predictive_planning_enabled = true
```

---

## 💻 **CodeAct Agent Configuration**

### **Basic Settings**

```toml
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

## 📋 **Agent Profiles**

### **Profile Locations**

```
Forge/Forge/agentic_behavior/
├── agent_profiles/
│   ├── product_manager.yaml
│   ├── architect.yaml
│   ├── engineer.yaml
│   ├── qa.yaml
│   └── ui_designer.yaml
```

### **Profile Structure**

```yaml
# Example: product_manager.yaml
role: "Product Manager"
persona: "Senior PM with 10+ years experience"

goal: |
  Create comprehensive product specifications with user stories,
  acceptance criteria, and prioritization.

skills:
  - "User story creation (INVEST principles)"
  - "Requirements gathering"
  - "Prioritization (MoSCoW, value vs effort)"
  - "Stakeholder communication"

expected_output_format:
  type: "json"
  schema: "pm_spec.schema.json"
  
constraints:
  - "Minimum 3-5 user stories"
  - "Each story must have 3-5 acceptance criteria"
  - "Include dependencies and priorities"

validation_rules:
  - "All stories must follow 'As a... I want... so that...' format"
  - "Each story must have estimated complexity"
  - "Must include assumptions and out-of-scope items"
```

### **Customize Profiles**

```toml
# config.toml
[metasop.profiles]
# Override default profile path
profiles_directory = "./custom_profiles"

# Profile-specific settings
[metasop.profiles.product_manager]
temperature = 0.7
max_tokens = 3000

[metasop.profiles.architect]
temperature = 0.5
max_tokens = 4000

[metasop.profiles.engineer]
temperature = 0.3
max_tokens = 4000
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

## 📝 **Examples**

### **Example 1: High-Performance Configuration**

```toml
# Fast responses, optimized for speed
[metasop]
enabled = true
max_retries_per_step = 1
step_timeout_seconds = 120

[metasop.orchestration]
parallel_execution = true
max_concurrent_agents = 5
auto_proceed = true

[agents.performance]
enable_streaming = true
parallel_tools = true
cache_enabled = true
```

### **Example 2: Conservative Configuration**

```toml
# Careful execution, optimized for accuracy
[metasop]
enabled = true
max_retries_per_step = 3
step_timeout_seconds = 600

[metasop.orchestration]
parallel_execution = false
max_concurrent_agents = 1
auto_proceed = false

[agents.retry]
max_retries = 5
initial_delay_seconds = 10
```

### **Example 3: Development Configuration**

```toml
# Fast iteration during development
[metasop]
enabled = true
default_template = "simple_app"

[metasop.agents]
product_manager = true
architect = false  # Skip for faster iteration
engineer = true
qa = false        # Skip for faster iteration
ui_designer = false

[codeact]
max_iterations = 10  # Lower for faster feedback
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

### **2. Agent-Task Matching**

```toml
# Simple tasks: Disable unnecessary agents
[metasop.agents]
product_manager = false
architect = false
engineer = true
qa = false

# Complex projects: Enable all agents
[metasop.agents]
product_manager = true
architect = true
engineer = true
qa = true
ui_designer = true
```

### **3. Performance vs Quality Trade-offs**

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
- [MetaSOP Overview](../features/metasop.md)
- [CodeAct Agent](../features/codeact-agent.md)

---

**Remember:** Agent configuration significantly impacts performance, cost, and quality. Choose settings appropriate for your use case!

