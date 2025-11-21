# Features

This page documents features that are implemented and available in Forge.

## Core Agents

### CodeAct Agent
- Executes code, runs commands, and edits files
- Integrated with file system and terminal tools
- Supports iterative development workflows
- Uses optimized prompts (system_prompt_forge.j2)

### Additional Agents
- **BrowsingAgent**: Web browsing and scraping capabilities
- **VisualBrowsingAgent**: Enhanced visual web interaction
- **LocAgent**: Location-aware operations
- **ReadOnlyAgent**: Read-only file operations
- **DummyAgent**: Testing and development agent

### MetaSOP Orchestration (Experimental)
- Multi-agent planning and execution framework
- Disabled by default (set `metasop.enabled = true` to activate)
- Role-based agents: Product Manager, Architect, Engineer, QA
- Structured task decomposition and coordination
- ACE (Agentic Context Engineering) framework integration

## APIs

Forge provides a comprehensive REST API with 32 route modules:

### Authentication & User Management
- **Authentication API** (`/api/auth`) - User registration, login, JWT token management
- **User Management API** (`/api/users`) - User CRUD operations, profile management, role-based access control

### Core Platform APIs
- **Conversations API** (`/api/conversations`) - Conversation lifecycle, message management
- **Files API** (`/api/files`) - File operations, workspace management
- **Settings API** (`/api/settings`) - User and system configuration
- **Secrets API** (`/api/secrets`) - Encrypted secrets storage and management

### Advanced Features
- **Knowledge Base API** (`/api/knowledge`) - Vector search, document management, collections
- **Memory API** (`/api/memory`) - Conversation memory and context management
- **MetaSOP API** (`/api/metasop`) - Multi-agent orchestration and coordination
- **Prompt Optimization API** (`/api/prompt-optimization`) - AI-powered prompt optimization

### Analytics & Monitoring
- **Analytics API** (`/api/analytics`) - Usage statistics, cost tracking, model usage
- **Monitoring API** (`/api/monitoring`) - Health checks, metrics, system status
- **Dashboard API** (`/api/dashboard`) - Quick stats, recent conversations, activity feed
- **Profile API** (`/api/profile`) - User statistics and activity timeline

### Platform Features
- **Search API** (`/api/search`) - Global search across conversations, files, snippets
- **Activity API** (`/api/activity`) - Activity feed and timeline
- **Notifications API** (`/api/notifications`) - User notifications management
- **Billing API** (`/api/billing`) - Payment processing, subscriptions, balance management

### Content Management
- **Snippets API** (`/api/snippets`) - Code snippet management
- **Templates API** (`/api/templates`) - Template management
- **Prompts API** (`/api/prompts`) - Prompt management
- **Trajectory API** (`/api/trajectory`) - Agent trajectory tracking and replay

### Integrations
- **Git API** (`/api/git`) - Git operations (OSS mode only)
- **Slack API** (`/api/slack`) - Slack integration
- **MCP API** (`/mcp`) - Model Context Protocol server
- **Database Connections API** (`/api/database`) - Database connection management

### WebSocket API (Socket.IO)
- Real-time communication for live updates
- Streaming agent responses
- Event-driven architecture
- Connection management and presence

### OpenAPI Documentation
- Interactive Swagger UI at `/docs`
- ReDoc alternative at `/redoc`
- OpenAPI JSON specification at `/openapi.json`

## Runtime Environments

### Docker Runtime
- Isolated execution environments
- Pre-built container images with Python/Node.js
- Support for multiple programming languages
- Sandboxed execution with configurable timeouts

### Local Runtime
- Direct execution on host system
- Faster startup for development
- Full system access (less secure)

### CLI Runtime
- Command-line interface execution
- Lightweight option for simple tasks

### Remote Runtime
- Execute on remote systems
- Distributed execution support

### Action Execution Runtime
- Specialized runtime for action execution
- Optimized for performance

### Warm Runtime Pool
- Reusable sandboxes keyed by runtime type + repo
- Reduced startup latency via warm reuse
- Per-key policies (`max_size`, `ttl_seconds`) from `ForgeConfig`
- Telemetry for idle reclaims and capacity evictions

## Tools and Integrations

### Core Tools
- **File Editor**: Create, read, update, delete files with search/replace
- **Terminal Commands**: Execute shell commands with output capture
- **Jupyter Support**: Execute Python code in notebook environments
- **Think Tool**: Advanced reasoning and problem-solving

### MCP (Model Context Protocol) Integrations
- **Shadcn UI**: React component library access
- **Fetch**: HTTP requests and HTML-to-markdown conversion
- **DuckDuckGo**: Web search capabilities
- **Playwright**: Browser automation (optional, resource-intensive)

### Version Control Integrations
- **GitHub**: Repository operations, PR management, issue tracking
- **GitLab**: GitLab repository and CI/CD integration
- **Bitbucket**: Bitbucket repository operations

### Communication Integrations
- **Slack**: Real-time messaging and notifications
- **VSCode Extension**: Integrated development environment support

## Microagents

Specialized agents for domain-specific tasks:
- Code review and testing
- Database operations
- Docker container management
- Git operations (GitHub, GitLab, Bitbucket)
- Kubernetes deployment
- NPM package management
- PDF generation
- SSH operations
- Security analysis

## Security

### Security Analyzer
- Code security scanning with multiple analyzers (LLM, Invariant)
- Vulnerability detection
- Safe execution policies

### Confirmation Mode
- User confirmation for potentially dangerous operations
- Granular permission controls
- Audit logging

### Sandboxing
- Isolated execution environments
- Configurable security policies
- Resource limits and timeouts

## Configuration

### Multiple LLM Support
- OpenAI GPT models (GPT-4, GPT-3.5, etc.)
- Anthropic Claude
- Google Gemini
- Other providers via LiteLLM
- Model-specific configurations and API key management

### Environment-Specific Configs
- Development, staging, production profiles
- Environment variable overrides
- Configuration validation and templating

## Experimental Features

### Causal Reasoning
- Conflict prediction in multi-agent scenarios
- Best-effort reasoning hooks
- Experimental implementation in MetaSOP

### Tree-sitter Analysis (Optional)
- Structural code analysis
- AST-based understanding
- Requires additional build dependencies

## Platform Features

### Session Management
- Conversation persistence and context retention
- Multi-session support with configurable limits
- Automatic conversation cleanup

### Logging and Monitoring
- Comprehensive logging with configurable levels
- Prometheus metrics and `/monitoring` endpoint
- Error tracking and reporting
- Runtime telemetry:
  - `forge_runtime_watchdog_watched` (gauge by kind)
  - `forge_runtime_pool_idle_reclaim_total`
  - `forge_runtime_pool_eviction_total`
  - `forge_runtime_scaling_signals_*` (overprovision, capacity_exhausted, saturation)
- MetaSOP guardrail metrics:
  - `metasop_guardrail_concurrency_total`
  - `metasop_guardrail_concurrency_peak`
  - `metasop_guardrail_runtime_avg_ms`

### Plugin System
- Extensible architecture for custom tools and agents
- Third-party integrations
- Runtime plugin initialization

## Eventing & Streaming

### EventStream
- Pub/sub with backpressure (drop_oldest/drop_newest/block)
- Async durability via `DurableEventWriter`
- Secret masking for tokens/credentials

### Event Service (in‑process)
- Start/Publish/Subscribe/Replay APIs
- Structured envelopes with type and metadata
- RPC metrics: totals, failures, latency

### Trajectory Recording
- Session replay capabilities
- Debugging and analysis support
- Configurable trajectory storage</content>
<parameter name="filePath">c:\Users\GIGABYTE\Desktop\Forge\docs_consolidated\features.md