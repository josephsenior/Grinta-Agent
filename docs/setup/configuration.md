# Configuration

Forge uses TOML configuration files and environment variables. All settings have defaults, so you only need to configure what you want to change.

## Configuration Files

- `config.toml` - Main configuration file
- `config.template.toml` - Template with all available options

## Core Settings

### LLM Configuration

```toml
[llm]
# Model to use
model = "gpt-4o"

# API key (set via environment variable FORGE_API_KEY)
api_key = ""

# Temperature for response randomness
temperature = 0.0

# Maximum output tokens
max_output_tokens = 0

# API base URL (for custom providers)
base_url = ""
```

### Agent Configuration

```toml
[agent]
# Enable/disable tools
enable_browsing = true
enable_editor = true
enable_cmd = true
enable_think = true

# LLM config to use
llm_config = "llm"

# Maximum iterations per task
max_iterations = 500
```

### Sandbox Configuration

```toml
[sandbox]
# Runtime environment
runtime = "docker"

# Container image
base_container_image = "nikolaik/python-nodejs:python3.12-nodejs22"

# Timeout in seconds
timeout = 120
```

## Environment Variables

Common environment variables:

- `FORGE_API_KEY` - LLM API key
- `FORGE_LLM_MODEL` - Model name
- `FORGE_RUNTIME` - Runtime environment (docker, local)
- `DEBUG` - Enable debug logging

## Production Deployment

For production, create `config.production.toml`:

```toml
[core]
debug = false

[sandbox]
timeout = 300

[llm]
temperature = 0.1
max_output_tokens = 4000
```

## Optional Features

### Browser Environment

```toml
[core]
enable_browser = true

[agent]
enable_browsing = true
```

```

### Security

```toml
[security]
enable_security_analyzer = true
confirmation_mode = false
```

## Advanced Configuration

### Custom LLM Providers

```toml
[llm.custom]
model = "your-model"
base_url = "https://your-provider.com"
api_key = "your-key"
```

### Multiple Agents

```toml
[agent.CodeActAgent]
llm_config = "llm"

[agent.RepoExplorerAgent]
llm_config = "gpt4o-mini"
```

### Kubernetes Runtime

```toml
[kubernetes]
namespace = "Forge"
resource_cpu_request = "1"
resource_memory_request = "1Gi"
```</content>
<parameter name="filePath">c:\Users\GIGABYTE\Desktop\Forge\docs_consolidated\configuration.md