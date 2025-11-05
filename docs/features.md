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

### Knowledge Base API
- REST endpoints for document management
- Vector search capabilities
- Collections and document CRUD operations

### WebSocket API
- Real-time communication for live updates
- Streaming agent responses
- Event-driven architecture

### REST API
- Full HTTP API for all platform features
- OpenAPI specification available
- Programmatic access to agents and tools

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

### Warm Server Pool
- Pre-initialized runtime servers
- Reduced startup latency
- Configurable pool sizes and cleanup policies

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
- Performance metrics and monitoring endpoints
- Error tracking and reporting

### Plugin System
- Extensible architecture for custom tools and agents
- Third-party integrations
- Runtime plugin initialization

### Trajectory Recording
- Session replay capabilities
- Debugging and analysis support
- Configurable trajectory storage</content>
<parameter name="filePath">c:\Users\GIGABYTE\Desktop\Forge\docs_consolidated\features.md