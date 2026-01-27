# API Reference

## Base URL

```
Development: http://localhost:3000
Production: https://api.forge.ai
```

**Note:** The server runs on port 3000 by default (configurable via `port` environment variable). The server serves both the REST API and the frontend SPA from the same port.

## Authentication

Forge supports multiple authentication methods:

1. **JWT Authentication** (when `AUTH_ENABLED=true`):
   - User registration and login
   - JWT token-based session management
   - Role-based access control (RBAC)

2. **API Key Authentication** (for LLM providers):
   - Secure API key management for 30+ LLM providers
   - Provider-specific key validation

See [Authentication Implementation](AUTHENTICATION_IMPLEMENTATION.md) for details.

## API Routes Overview

Forge provides 32 route modules covering all platform features:

- **Authentication** (`/api/auth`) - User registration, login, session management
- **User Management** (`/api/users`) - User CRUD operations, profile management
- **Conversations** (`/api/conversations`) - Conversation lifecycle management
- **Files** (`/api/files`) - File operations and workspace management
- **Settings** (`/api/settings`) - User and system configuration
- **Secrets** (`/api/secrets`) - Encrypted secrets storage
- **Memory** (`/api/memory`) - Conversation memory and context management
- **Knowledge Base** (`/api/knowledge`) - Vector search and document management
- **Monitoring** (`/api/monitoring`) - Health checks, metrics, and system status
- **Analytics** (`/api/analytics`) - Usage statistics and reporting
- **Billing** (`/api/billing`) - Payment processing and subscriptions
- **Dashboard** (`/api/dashboard`) - Dashboard data and quick stats
- **Profile** (`/api/profile`) - User profile and statistics
- **Search** (`/api/search`) - Global search across resources
- **Activity** (`/api/activity`) - Activity feed and timeline
- **Notifications** (`/api/notifications`) - User notifications
- **Prompt Optimization** (`/api/prompt-optimization`) - AI-powered prompt optimization
- **Templates** (`/api/templates`) - Template management
- **Trajectory** (`/api/trajectory`) - Agent trajectory tracking
- **Security** (`/api/security`) - Security features and audit logs
- **Feedback** (`/api/feedback`) - User feedback collection
- **Database Connections** (`/api/database`) - Database connection management
- **Git** (`/api/git`) - Git operations (OSS mode only)
- **Slack** (`/api/slack`) - Slack integration
- **MCP** (`/mcp`) - Model Context Protocol server
- **Public** (`/api/public`) - Public endpoints
- **Global Export** (`/api/export`) - Data export functionality
- **Health** (`/api/health`) - Health check endpoints

## Core Endpoints

### Authentication

#### Register User

```http
POST /api/auth/register
```

**Request:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "user_123abc",
    "email": "user@example.com",
    "username": "johndoe",
    "created_at": "2025-11-04T10:00:00Z"
  }
}
```

#### Login

```http
POST /api/auth/login
```

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "id": "user_123abc",
      "email": "user@example.com",
      "username": "johndoe"
    }
  }
}
```

### User Management

#### List Users

```http
GET /api/users?page=1&limit=20
```

#### Get User

```http
GET /api/users/{user_id}
```

#### Update User

```http
PUT /api/users/{user_id}
```

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
GET /api/monitoring/health
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

### Billing

#### Create Checkout Session

```http
POST /api/billing/checkout
```

**Request:**
```json
{
  "amount": 100
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "redirect_url": "https://checkout.stripe.com/..."
  }
}
```

#### Get Balance

```http
GET /api/billing/balance
```

### Dashboard

#### Get Quick Stats

```http
GET /api/dashboard/stats
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_conversations": 45,
    "active_conversations": 5,
    "total_cost": 123.45,
    "success_rate": 95.5
  }
}
```

#### Get Recent Conversations

```http
GET /api/dashboard/recent-conversations?limit=10
```

### Profile

#### Get User Statistics

```http
GET /api/profile/statistics
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_conversations": 45,
    "active_conversations": 5,
    "total_cost": 123.45,
    "success_rate": 95.5,
    "total_tokens": 2000000,
    "avg_response_time": 850.5
  }
}
```

#### Get Activity Timeline

```http
GET /api/profile/activity?limit=20
```

### Search

#### Global Search

```http
GET /api/search?q=query&type=conversations
```

**Response:**
```json
{
  "success": true,
  "data": {
    "query": "query",
    "results": [
      {
        "id": "conv_123",
        "type": "conversation",
        "title": "Build todo app",
        "description": "A todo application",
        "url": "/conversations/conv_123",
        "metadata": {}
      }
    ],
    "total": 1
  }
}
```

### Activity

#### Get Activity Feed

```http
GET /api/activity?type=conversation&page=1&limit=20
```

**Response:**
```json
{
  "success": true,
  "data": {
    "activities": [
      {
        "id": "act_123",
        "type": "conversation_created",
        "timestamp": "2025-11-04T10:00:00Z",
        "metadata": {
          "conversation_id": "conv_123",
          "title": "Build todo app"
        }
      }
    ],
    "total": 1
  }
}
```

### Notifications

#### Get Notifications

```http
GET /api/notifications?unread_only=true
```

### Secrets

#### Create Secret

```http
POST /api/secrets
```

**Request:**
```json
{
  "key": "OPENAI_API_KEY",
  "value": "sk-...",
  "description": "OpenAI API key"
}
```

#### List Secrets

```http
GET /api/secrets
```

### Memory

#### Get Conversation Memory

```http
GET /api/memory/conversations/{conversation_id}
```

### Knowledge Base

#### Create Collection

```http
POST /api/knowledge/collections
```

#### Search Documents

```http
GET /api/knowledge/search?collection_id=col_123&query=search term
```

### Templates

#### List Templates

```http
GET /api/templates
```

### Trajectory

#### Get Agent Trajectory

```http
GET /api/trajectory/conversations/{conversation_id}
```

## WebSocket API (Socket.IO)

The backend uses Socket.IO for real-time communication, not plain WebSocket.

### Connect

```javascript
import { io } from 'socket.io-client';

const socket = io('http://localhost:3000', {
  path: '/socket.io',
  query: {
    conversationId: '{conversation_id}',
  },
  transports: ['websocket', 'polling'],
});
```

### Events

#### Receive Events

```javascript
socket.on('message', (event) => {
  // Event is already parsed JSON
  if (event.observation === 'agent_state_changed') {
    console.log('Agent state:', event.extras.agent_state);
  } else if (event.action) {
    console.log('Action:', event.action);
  } else if (event.observation) {
    console.log('Observation:', event.observation);
  }
});
```

#### Send Message

```javascript
socket.emit('oh_user_action', {
  action: 'message',
  content: 'Build a todo app'
});
```

#### Control Agent

```javascript
// Pause agent
socket.emit('oh_user_action', { action: 'pause' });

// Resume agent
socket.emit('oh_user_action', { action: 'resume' });

// Stop agent
socket.emit('oh_user_action', { action: 'stop' });
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
pnpm add @Forge/sdk
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

**Note:** The OpenAPI specification is automatically generated from the FastAPI application and includes all registered routes from `forge/server/routes/`.

## Versioning

API versioning via headers (optional, beta allows non-versioned):

```http
GET /api/settings
Accept: application/vnd.Forge.v1+json
```

See [API Versioning Guide](./api-versioning-guide.md) for details.

## References

- [Architecture](./architecture.md) - System design
- [Monitoring](./monitoring.md) - Metrics and alerts
- [Security](./security.md) - Security policies
- [Troubleshooting](./troubleshooting.md) - Common issues

