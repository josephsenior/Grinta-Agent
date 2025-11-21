# Quick Reference Guide

Quick reference for common Forge commands, configurations, and patterns.

## Command Line

### Starting Forge

```bash
# Start backend
poetry run python -m forge.server

# Start frontend (development)
cd frontend && npm run dev

# Start frontend (production build)
cd frontend && npm run build && npm run preview
```

### Running Tests

```bash
# All unit tests
poetry run pytest tests/unit/

# Specific test file
poetry run pytest tests/unit/test_agent.py

# With coverage
poetry run pytest --cov=forge tests/unit/

# Integration tests
poetry run pytest tests/integration/

# E2E tests
poetry run pytest tests/e2e/
```

### Development

```bash
# Install dependencies
poetry install
cd frontend && npm install

# Format code
poetry run black forge/
poetry run ruff format forge/

# Lint code
poetry run ruff check forge/
poetry run mypy forge/

# Type check frontend
cd frontend && npm run type-check
```

## Environment Variables

### Required

```bash
# At least one LLM provider
ANTHROPIC_API_KEY=sk-ant-...
# OR
OPENAI_API_KEY=sk-...
# OR
OPENROUTER_API_KEY=sk-or-...

# Model selection
LLM_MODEL=claude-sonnet-4-20250514
```

### Optional

```bash
# Server configuration
PORT=3000
HOST=0.0.0.0

# Authentication
AUTH_ENABLED=true
JWT_SECRET=your-secret-key

# Redis (for caching/rate limiting)
REDIS_URL=redis://localhost:6379

# Database
DATABASE_URL=postgresql://user:pass@localhost/forge

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
```

## API Endpoints

### Authentication

```bash
# Register
POST /api/auth/register
Body: { "email": "...", "password": "..." }

# Login
POST /api/auth/login
Body: { "email": "...", "password": "..." }

# Get current user
GET /api/auth/me
Headers: { "Authorization": "Bearer <token>" }
```

### Conversations

```bash
# List conversations
GET /api/conversations

# Create conversation
POST /api/conversations
Body: { "title": "...", "workspace": "..." }

# Get conversation
GET /api/conversations/{id}

# Send message
POST /api/conversations/{id}/messages
Body: { "content": "..." }
```

### Files

```bash
# List files
GET /api/files?path=/

# Read file
GET /api/files?path=/path/to/file

# Write file
POST /api/files
Body: { "path": "...", "content": "..." }

# Delete file
DELETE /api/files?path=/path/to/file
```

## WebSocket Events

### Client → Server

```javascript
// Join conversation
socket.emit('join_conversation', { conversation_id: '...' })

// Send message
socket.emit('message', { 
  conversation_id: '...',
  content: '...'
})

// Leave conversation
socket.emit('leave_conversation', { conversation_id: '...' })
```

### Server → Client

```javascript
// Message received
socket.on('message', (data) => {
  // Handle message
})

// Agent thought
socket.on('agent_thought', (data) => {
  // Handle thought
})

// Action executed
socket.on('action', (data) => {
  // Handle action
})
```

## Python SDK

### Basic Usage

```python
from forge.client import ForgeClient

client = ForgeClient(
    base_url="http://localhost:3000",
    api_key="your-api-key"
)

# Create conversation
conversation = client.conversations.create(
    title="My Conversation",
    workspace="/path/to/workspace"
)

# Send message
response = client.conversations.send_message(
    conversation_id=conversation.id,
    content="Hello, agent!"
)
```

## TypeScript SDK

### Basic Usage

```typescript
import { ForgeClient } from '@forge/sdk';

const client = new ForgeClient({
  baseURL: 'http://localhost:3000',
  apiKey: 'your-api-key'
});

// Create conversation
const conversation = await client.conversations.create({
  title: 'My Conversation',
  workspace: '/path/to/workspace'
});

// Send message
const response = await client.conversations.sendMessage(
  conversation.id,
  'Hello, agent!'
);
```

## Agent Prompts

### CodeAct Agent

```
Can you [action] in [file]?

Examples:
- "Can you add error handling to the login function?"
- "Can you refactor the UserService class?"
- "Can you write tests for the API endpoints?"
```

### MetaSOP Orchestration

```
I want to build [project description]. 
Can you break this down into steps and execute them?

Examples:
- "I want to build a REST API for a todo app"
- "I want to create a React component library"
```

## File Paths

### Backend

```
forge/
├── server/          # FastAPI server
├── agenthub/        # Agent implementations
├── llm/             # LLM provider system
├── controller/      # Agent controller
├── runtime/         # Runtime environments
└── memory/          # Memory system
```

### Frontend

```
frontend/
├── src/
│   ├── components/  # React components
│   ├── routes/      # Route definitions
│   ├── store/       # Redux store
│   └── api/         # API clients
└── tests/           # Frontend tests
```

## Common Patterns

### Error Handling

```python
try:
    result = agent.execute(action)
except AgentError as e:
    # Handle agent error
    logger.error(f"Agent error: {e}")
except RuntimeError as e:
    # Handle runtime error
    logger.error(f"Runtime error: {e}")
```

### Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def call_llm(prompt):
    return llm_client.generate(prompt)
```

### Monitoring

```python
from forge.monitoring import metrics

# Record metric
metrics.record_latency("agent.execute", duration_ms)

# Increment counter
metrics.increment("agent.actions.executed")
```

## Troubleshooting

### Backend won't start

```bash
# Check Python version
python --version  # Should be 3.11+

# Check dependencies
poetry check

# Check port availability
lsof -i :3000  # Linux/Mac
netstat -ano | findstr :3000  # Windows
```

### Frontend won't start

```bash
# Check Node version
node --version  # Should be 18+

# Clear cache
rm -rf node_modules package-lock.json
npm install

# Check port availability
lsof -i :5173  # Linux/Mac
netstat -ano | findstr :5173  # Windows
```

### Agent not responding

```bash
# Check LLM API key
echo $ANTHROPIC_API_KEY  # Or your provider

# Check logs
tail -f logs/forge.log

# Test LLM connection
poetry run python -c "from forge.llm import test_connection; test_connection()"
```

## Resources

- [Full Documentation](../docs/index.md)
- [API Reference](../docs/api-reference.md)
- [Troubleshooting Guide](../docs/troubleshooting.md)
- [Best Practices](../docs/guides/best-practices.md)

