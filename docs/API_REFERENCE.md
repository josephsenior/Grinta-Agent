# API Reference

## Base URL

```
Development: http://localhost:3000
Production: https://api.Forge.dev
```

## Authentication

Currently using API key-based authentication for LLM providers. User authentication system in development.

## Core Endpoints

### Conversations

#### Create Conversation

```http
POST /api/conversations
```

**Request:**
```json
{
  "title": "Build todo app",
  "repository": "https://github.com/user/repo" // optional
}
```

**Response:**
```json
{
  "conversation_id": "conv_123abc",
  "created_at": "2025-11-04T10:00:00Z",
  "status": "active"
}
```

#### List Conversations

```http
GET /api/conversations
```

**Response:**
```json
{
  "conversations": [
    {
      "id": "conv_123abc",
      "title": "Build todo app",
      "created_at": "2025-11-04T10:00:00Z",
      "message_count": 15,
      "status": "active"
    }
  ],
  "total": 42
}
```

#### Get Conversation

```http
GET /api/conversations/{conversation_id}
```

#### Delete Conversation

```http
DELETE /api/conversations/{conversation_id}
```

### Messages

#### Send Message

```http
POST /api/conversations/{conversation_id}/messages
```

**Request:**
```json
{
  "content": "Fix the bug in main.py line 42",
  "attachments": [] // optional
}
```

**Response:**
```json
{
  "message_id": "msg_456def",
  "status": "sent",
  "timestamp": "2025-11-04T10:01:00Z"
}
```

### Settings

#### Get Settings

```http
GET /api/settings
```

**Response:**
```json
{
  "llm": {
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.0,
    "max_output_tokens": 8000
  },
  "agent": {
    "type": "CodeActAgent",
    "max_iterations": 100
  },
  "security": {
    "confirmation_mode": "enabled",
    "sandbox_type": "docker"
  }
}
```

#### Update Settings

```http
PUT /api/settings
```

**Request:**
```json
{
  "llm": {
    "model": "gpt-4o",
    "temperature": 0.1
  }
}
```

### Health & Monitoring

#### Health Check

```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0-beta",
  "uptime_seconds": 86400,
  "database": "connected",
  "llm_provider": "anthropic"
}
```

#### Metrics

```http
GET /api/monitoring/metrics
```

**Response:**
```json
{
  "system": {
    "active_conversations": 5,
    "total_actions_today": 1234,
    "avg_response_time_ms": 850,
    "cache_stats": {
      "hits": 456,
      "stores": 123,
      "hit_rate": 78.8
    }
  },
  "agents": [
    {
      "agent_name": "CodeActAgent",
      "total_actions": 1000,
      "successful_actions": 950,
      "success_rate": 95.0
    }
  ]
}
```

### Files

#### List Files

```http
GET /api/files?path=/src
```

**Response:**
```json
{
  "files": [
    {
      "path": "/src/main.py",
      "size": 1024,
      "modified": "2025-11-04T09:00:00Z"
    }
  ]
}
```

#### Read File

```http
GET /api/files/content?path=/src/main.py
```

**Response:**
```json
{
  "path": "/src/main.py",
  "content": "def main():\n    print('Hello')\n",
  "size": 1024
}
```

### Analytics

#### Get Usage Stats

```http
GET /api/analytics/usage?period=week
```

**Response:**
```json
{
  "period": "week",
  "conversations": 45,
  "messages": 678,
  "cost_usd": 12.34,
  "tokens": {
    "input": 1500000,
    "output": 500000
  }
}
```

#### Get Model Usage

```http
GET /api/analytics/models?period=week
```

**Response:**
```json
[
  {
    "model": "claude-sonnet-4-20250514",
    "conversations": 30,
    "cost_usd": 8.50,
    "tokens": 1200000
  },
  {
    "model": "gpt-4o",
    "conversations": 15,
    "cost_usd": 3.84,
    "tokens": 800000
  }
]
```

## WebSocket API

### Connect

```javascript
const ws = new WebSocket('ws://localhost:3000/ws/conversations/{conversation_id}');
```

### Events

#### Receive Events

```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'action':
      // Agent performed an action
      console.log('Action:', data.content);
      break;
    case 'observation':
      // Action result received
      console.log('Result:', data.content);
      break;
    case 'state_change':
      // Agent state changed
      console.log('State:', data.state);
      break;
  }
};
```

#### Send Message

```javascript
ws.send(JSON.stringify({
  type: 'message',
  content: 'Build a todo app'
}));
```

#### Control Agent

```javascript
// Pause agent
ws.send(JSON.stringify({ type: 'pause' }));

// Resume agent
ws.send(JSON.stringify({ type: 'resume' }));

// Stop agent
ws.send(JSON.stringify({ type: 'stop' }));
```

## Rate Limits

### Current Limits (Beta)

| Tier | Requests/Hour | Requests/Minute | Daily Cost Limit |
|------|---------------|-----------------|------------------|
| Free | 1000 | 100 | $1.00 |
| Pro | 5000 | 500 | $10.00 |
| Team | 10000 | 1000 | $50.00 |

### Rate Limit Headers

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 856
X-RateLimit-Reset: 1699123456
```

### Rate Limit Error

```json
{
  "error": {
    "type": "rate_limit_exceeded",
    "message": "Rate limit exceeded. Please try again in 45 seconds.",
    "retry_after": 45
  }
}
```

## Error Handling

### Error Response Format

All errors follow this structure:

```json
{
  "error": {
    "type": "validation_error",
    "message": "User-friendly error message",
    "details": "Technical details for debugging",
    "actions": [
      {
        "label": "Retry",
        "action": "retry"
      }
    ],
    "help_url": "https://docs.Forge.dev/errors/validation"
  }
}
```

### Common Error Types

| Type | HTTP Code | Meaning |
|------|-----------|---------|
| `invalid_api_key` | 401 | LLM API key invalid or missing |
| `rate_limit_exceeded` | 429 | Too many requests |
| `quota_exceeded` | 402 | Daily cost limit reached |
| `validation_error` | 400 | Invalid request parameters |
| `agent_error` | 500 | Agent execution failed |
| `llm_error` | 502 | LLM provider error |

## Models

### List Available Models

```http
GET /api/options/models
```

**Response:**
```json
[
  "claude-sonnet-4-20250514",
  "claude-haiku-4-5-20251001",
  "gpt-4o",
  "gpt-4o-mini",
  "openrouter/anthropic/claude-3.5-sonnet",
  "openrouter/x-ai/grok-4-fast",
  ... 200+ more models
]
```

### List Available Agents

```http
GET /api/options/agents
```

**Response:**
```json
[
  "CodeActAgent",
  "PlannerAgent",
  "BrowseAgent"
]
```

## TypeScript SDK

### Installation

```bash
npm install @Forge/sdk
```

### Usage

```typescript
import { ForgeClient } from '@Forge/sdk';

const client = new ForgeClient({
  baseUrl: 'http://localhost:3000',
});

// Create conversation
const conversation = await client.conversations.create({
  title: 'Build todo app'
});

// Send message
await client.conversations.sendMessage(conversation.id, {
  content: 'Build a React todo app'
});

// Listen to events
client.conversations.subscribe(conversation.id, (event) => {
  console.log('Event:', event);
});
```

## Python SDK

### Installation

```bash
pip install Forge-sdk
```

### Usage

```python
from forge_sdk import forgeClient

client = ForgeClient(base_url='http://localhost:3000')

# Create conversation
conversation = client.conversations.create(title='Build todo app')

# Send message
response = client.conversations.send_message(
    conversation.id,
    content='Build a Python Flask todo API'
)

# Get conversation history
messages = client.conversations.get_messages(conversation.id)
```

## OpenAPI Specification

**Interactive Documentation:**
- Swagger UI: `http://localhost:3000/docs`
- ReDoc: `http://localhost:3000/redoc`
- OpenAPI JSON: `http://localhost:3000/openapi.json`

## Versioning

API versioning via headers (optional, beta allows non-versioned):

```http
GET /api/settings
Accept: application/vnd.Forge.v1+json
```

See [API Versioning Guide](./api-versioning-guide.md) for details.

## References

- [Architecture](./ARCHITECTURE.md) - System design
- [Monitoring](./MONITORING.md) - Metrics and alerts
- [Security](./security.md) - Security policies
- [Troubleshooting](./TROUBLESHOOTING.md) - Common issues

