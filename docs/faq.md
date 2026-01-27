# Frequently Asked Questions (FAQ)

## General

### What is Forge?

Forge is an AI-powered development platform that helps developers build software with intelligent AI agents. It provides structure-aware code editing, multi-agent orchestration, and production-grade infrastructure for AI-assisted development.

### Is Forge production-ready?

Yes! Forge is production-ready with a **9.5/10** rating. It includes:
- Enterprise-grade error handling (Circuit Breaker, exponential backoff)
- Comprehensive monitoring (Prometheus + Grafana)
- 113,880+ lines of test code (5,073+ test cases)
- Zero high-complexity functions
- Production deployment guides

See [Code Quality](code-quality.md) and [Production Deployment](production_deployment.md) for details.

### What makes Forge different from other AI coding assistants?

**Key Differentiators:**
- **Ultimate Editor**: Structure-aware editing with Tree-sitter (45+ languages)
- **Multi-agent Coordination**: Efficient planning and execution
- **Production Infrastructure**: Circuit breakers, monitoring, cost quotas
- **Comprehensive Testing**: 113k+ lines of test code
- **30+ LLM Providers**: Support for 200+ models via unified API

See [Comparisons](comparisons/) for detailed comparisons with Cursor, Copilot, etc.

---

## Getting Started

### What are the prerequisites?

- **Python**: 3.11 or higher
- **Node.js**: 18 or higher
- **Docker**: For sandbox execution
- **Git**: For version control
- **Poetry**: For Python dependency management (recommended)

See [Getting Started](getting_started.md) for detailed setup instructions.

### How do I configure my first LLM provider?

**Option 1: Anthropic Claude (Recommended)**
```bash
# In .env file:
LLM_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Option 2: OpenRouter (200+ Models)**
```bash
# In .env file:
LLM_MODEL=openrouter/anthropic/claude-3.5-sonnet
OPENROUTER_API_KEY=sk-or-your-key-here
```

**Option 3: OpenAI**
```bash
# In .env file:
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-your-key-here
```

See [Configuration](configuration.md) for complete setup.

### How do I start the application?

1. **Start backend:**
```bash
poetry run python -m forge.server
```

2. **Start frontend (in new terminal):**
```bash
cd frontend
pnpm run dev
```

3. **Open browser:**
```
http://localhost:5173
```

See [Getting Started](getting_started.md) for details.

---

## Features

### What is the Ultimate Editor?

The Ultimate Editor is Forge's structure-aware code editing system that uses Tree-sitter to understand code structure across 45+ languages. It enables:
- Atomic refactoring across multiple files
- Structure-aware edits (not just text replacement)
- Safe code transformations
- Multi-file operations

See [Ultimate Editor Guide](ultimate-editor.md) for details.

### What agents are available?

- **CodeAct Agent**: Code editing and command execution
- **BrowsingAgent**: Web browsing and scraping
- **LocAgent**: Location-aware operations
- **ReadOnlyAgent**: Read-only file operations
- **DummyAgent**: Testing and development

See [Features](features.md) for complete list.

---

## API & Integration

### How do I use the REST API?

Forge provides a comprehensive REST API with 32 route modules. See [API Reference](api-reference.md) for complete documentation.

**Base URL:**
```
Development: http://localhost:3000
Production: https://api.forge.ai
```

**Authentication:**
- JWT tokens (when `AUTH_ENABLED=true`)
- API keys for LLM providers

### Is there a Python SDK?

Yes! See [Python SDK Documentation](api/python-sdk.md) for details.

### Is there a TypeScript SDK?

Yes! See [TypeScript SDK Documentation](api/typescript-sdk.md) for details.

### How do I use WebSocket for real-time communication?

Forge uses Socket.IO for real-time communication. See [WebSocket API Documentation](api/websocket-api.md) for details.

---

## Configuration

### How do I configure multiple LLM providers?

You can configure multiple providers in your `.env` file:

```bash
# Primary model
LLM_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-...

# Fallback providers
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
```

The system will automatically fallback if the primary provider fails.

See [Configuration Guide](configuration.md) for details.

### How do I set up cost quotas?

Cost quotas track spending in dollars, not just requests. Configure in your settings:

```python
# Free tier: $1/day
COST_QUOTA_DAILY=1.0

# Pro tier: $10/day
COST_QUOTA_DAILY=10.0
```

See [Cost Quotas](forge/server/middleware/cost_quota.py) for implementation details.

### How do I configure monitoring?

Forge includes Prometheus + Grafana monitoring. See [Monitoring Guide](monitoring.md) for setup instructions.

---

## Troubleshooting

### "No API key found for provider"

**Solution:**
1. Check your `.env` file has the correct API key
2. Verify the key format matches the provider:
   - OpenAI: `sk-...`
   - Anthropic: `sk-ant-...`
   - OpenRouter: `sk-or-...`
3. Restart the backend server

See [Troubleshooting Guide](troubleshooting.md) for more solutions.

### "Docker not running" error

**Solution:**
1. Start Docker Desktop
2. Verify Docker is running: `docker ps`
3. Check Docker daemon is accessible

See [Troubleshooting Guide](TROUBLESHOOTING.md) for details.

### Agent seems stuck or not responding

**Solution:**
1. Check the Circuit Breaker status in monitoring
2. Review error logs for specific failures
3. Verify LLM provider is responding
4. Check rate limits haven't been exceeded

See [Troubleshooting Guide](TROUBLESHOOTING.md) for debugging steps.

---

## Development

### How do I contribute?

See [Contributing Guide](contributing.md) for:
- Code of conduct
- Development setup
- Pull request process
- Good first issues

### How do I run tests?

**Unit tests:**
```bash
poetry run pytest tests/unit/
```

**Integration tests:**
```bash
poetry run pytest tests/integration/
```

**E2E tests:**
```bash
poetry run pytest tests/e2e/
```

See [Testing Guide](testing.md) for complete instructions.

### What's the code quality standard?

Forge maintains high code quality:
- **Backend average complexity**: 3.06 (A-rated) across 8,100 functions/methods
- **Frontend average complexity**: 2.21 (A-rated)
- **0% high-complexity functions** (0 above B complexity level)
- **High-complexity functions**: 0%
- **A-rated functions**: 85.8%
- **Test coverage**: 113,880+ lines of test code

See [Code Quality](code-quality.md) for metrics.

---

## Deployment

### How do I deploy to production?

See [Production Deployment Guide](production_deployment.md) for:
- Server configuration
- Scaling strategies
- Monitoring setup
- Security hardening

### What are the system requirements?

**Minimum:**
- 4 CPU cores
- 8GB RAM
- 20GB disk space
- Docker installed

**Recommended:**
- 8+ CPU cores
- 16GB+ RAM
- 50GB+ disk space
- Redis for caching

See [Production Deployment](production_deployment.md) for details.

### How do I scale horizontally?

Forge supports horizontal scaling:
- Multiple server instances
- Redis for distributed caching
- Load balancer support
- Kubernetes runtime support

See [Architecture](architecture.md) for scaling details.

---

## Security

### How is user data secured?

- JWT authentication
- Encrypted secrets storage
- Docker sandboxing for code execution
- Security headers middleware
- CSRF protection

See [Security Policy](security.md) for details.

### What security scanning is performed?

- **Bandit**: Python security linter
- **Flake8**: Code quality checking
- **Ruff**: Fast Python linter with security rules
- **Manual code review**: For critical security concerns

See [Security Policy](security.md) for current status.

---

## Performance

### What's the typical response time?

- **p50 latency**: < 500ms
- **p95 latency**: < 2000ms
- **p99 latency**: < 5000ms

See [Monitoring Guide](monitoring.md) for performance metrics.

### How do I optimize performance?

- Enable prompt caching
- Use warm runtime pools
- Configure Redis caching
- Optimize LLM model selection

See [Performance Tuning Guide](guides/performance-tuning.md) for tips.

---

## Support

### Where can I get help?

- **Documentation**: [docs/](index.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/Forge/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/Forge/discussions)

### How do I report a bug?

1. Check [Troubleshooting Guide](troubleshooting.md) first
2. Search [existing issues](https://github.com/yourusername/Forge/issues)
3. Create a new issue with:
   - Description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details

---

## License

Forge is licensed under the MIT License. See [LICENSE](../LICENSE) for details.

