# 🌐 **REST API Reference**

> **Comprehensive REST API documentation for the Forge platform, covering all endpoints, request/response formats, and authentication.**

---

## 📖 **Table of Contents**

- [🌟 Overview](#-overview)
- [🔐 Authentication](#-authentication)
- [📊 Base URLs](#-base-urls)
- [🤖 Agent Endpoints](#-agent-endpoints)
- [⚡ Optimization Endpoints](#-optimization-endpoints)
- [💾 Memory Endpoints](#-memory-endpoints)
- [🔧 Tool Endpoints](#-tool-endpoints)
- [📈 Monitoring Endpoints](#-monitoring-endpoints)
- [🎯 WebSocket Endpoints](#-websocket-endpoints)
- [🔍 Error Handling](#-error-handling)
- [📚 Examples](#-examples)

---

## 🌟 **Overview**

The Forge REST API provides comprehensive access to all platform features through HTTP endpoints. The API follows RESTful principles and uses JSON for data exchange.

### **API Features**
- **RESTful Design**: Standard HTTP methods and status codes
- **JSON Format**: All requests and responses use JSON
- **Authentication**: JWT-based authentication
- **Rate Limiting**: Built-in rate limiting for API protection
- **CORS Support**: Cross-origin resource sharing enabled
- **WebSocket Support**: Real-time communication via WebSocket

### **API Versioning**
- **Current Version**: v1
- **Version Header**: `API-Version: v1`
- **URL Versioning**: `/api/v1/endpoint`

---

## 🔐 **Authentication**

### **Authentication Methods**
1. **JWT Token**: Bearer token in Authorization header
2. **API Key**: X-API-Key header (for service-to-service)
3. **Session Cookie**: HTTP-only cookie (for web clients)

### **Authentication Headers**
```http
# JWT Token
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# API Key
X-API-Key: your-api-key-here

# Session Cookie
Cookie: session_id=your-session-id
```

### **Authentication**

Forge currently uses session-based authentication for Socket.IO connections and API key-based authentication for LLM providers. User authentication endpoints are not yet implemented in the current backend.

**Session Authentication (Socket.IO):**
- Sessions are created when a conversation is initialized via `POST /api/conversations`
- Session API keys are returned in the conversation response
- Socket.IO connections require `conversationId` and optionally `session_api_key` in query parameters

**LLM Provider Authentication:**
- API keys are configured via settings: `POST /api/settings`
- Keys are stored securely and used for LLM API calls

---

## 📊 **Base URLs**

### **Development**
```
http://localhost:3000/api
```

**Note:** The server runs on port 3000 by default (configurable via `port` environment variable). API versioning is handled via headers, not URL paths. All routes are under `/api/` prefix.

### **Staging**
```
https://staging-api.forge.ai/api
```

### **Production**
```
https://api.forge.ai/api
```

### **WebSocket URLs (Socket.IO)**
```
# Development
http://localhost:3000/socket.io

# Staging
https://staging-api.forge.ai/socket.io

# Production
https://api.forge.ai/socket.io
```

**Note:** Socket.IO automatically handles WebSocket upgrade. Use the Socket.IO client library, not raw WebSocket.

---

## 🤖 **Agent Endpoints**

### **Conversation Management**

Agent execution is managed through conversations. Create a conversation, then start the agent loop.

#### **Create Conversation**
```http
POST /api/conversations
Content-Type: application/json

{
  "repository": "https://github.com/user/repo",
  "git_provider": "github",
  "selected_branch": "main",
  "initial_user_msg": "Create a user authentication system"
}
```

**Response:**
```json
{
  "status": "success",
  "conversation_id": "conv_123abc",
  "conversation_status": "STOPPED",
  "message": null
}
```

#### **Start Conversation (Agent Loop)**
```http
POST /api/conversations/{conversation_id}/start
Content-Type: application/json

{
  "providers_set": ["github"]
}
```

**Response:**
```json
{
  "status": "success",
  "conversation_id": "conv_123abc",
  "conversation_status": "STARTING",
  "message": null
}
```

#### **Stop Conversation**
```http
POST /api/conversations/{conversation_id}/stop
```

#### **Get Conversation Status**
```http
GET /api/conversations/{conversation_id}
```

**Response:**
```json
{
  "conversation_id": "conv_123abc",
  "title": "Create a user authentication system",
  "status": "RUNNING",
  "runtime_status": "STATUS$READY",
  "last_updated_at": "2025-01-15T10:30:00Z",
  "created_at": "2025-01-15T10:00:00Z"
}
```

#### **Get Agent Health (Controller)**
```http
GET /api/monitoring/controller/{session_id}/health
```

Returns detailed health information about the agent controller including state, iteration usage, and safety services.

---

## ⚡ **Optimization Endpoints**

### **Prompt Optimization**

#### **Get Optimization Status**
```http
GET /api/optimization/status
Authorization: Bearer your-token
```

**Response:**
```json
{
  "success": true,
  "status": {
    "enabled": true,
    "active_variants": 15,
    "total_prompts": 25,
    "optimizations_performed": 150,
    "performance_improvement": 0.23,
    "cost_savings": 0.15
  }
}
```

#### **Trigger Optimization**
```http
POST /api/optimization/trigger
Authorization: Bearer your-token
Content-Type: application/json

{
  "prompt_id": "system_prompt_1",
  "priority": 8,
  "context": {
    "reason": "performance_drop",
    "current_performance": 0.65,
    "target_performance": 0.8
  }
}
```

**Response:**
```json
{
  "success": true,
  "optimization": {
    "event_id": "opt_123",
    "prompt_id": "system_prompt_1",
    "status": "triggered",
    "priority": 8,
    "estimated_completion": "2024-01-15T10:35:00Z"
  }
}
```

#### **Get Performance Metrics**
```http
GET /api/optimization/metrics/{prompt_id}
Authorization: Bearer your-token
```

**Response:**
```json
{
  "success": true,
  "metrics": {
    "prompt_id": "system_prompt_1",
    "total_executions": 150,
    "success_rate": 0.85,
    "average_execution_time": 2.3,
    "average_cost": 0.05,
    "error_rate": 0.15,
    "optimization_improvement": 0.23,
    "cost_savings": 0.15
  }
}
```

### **Real-Time Optimization**

#### **Get Real-Time Status**
```http
GET /api/optimization/realtime/status
Authorization: Bearer your-token
```

**Response:**
```json
{
  "success": true,
  "status": {
    "enabled": true,
    "is_running": true,
    "active_optimizations": 3,
    "hot_swaps_performed": 25,
    "performance_predictions": 150,
    "streaming_events_processed": 1250
  }
}
```

#### **Trigger Real-Time Optimization**
```http
POST /api/optimization/realtime/trigger
Authorization: Bearer your-token
Content-Type: application/json

{
  "prompt_id": "system_prompt_1",
  "priority": 8,
  "context": {
    "reason": "performance_drop",
    "performance_drop": 0.15
  }
}
```

**Response:**
```json
{
  "success": true,
  "optimization": {
    "event_id": "rt_opt_123",
    "prompt_id": "system_prompt_1",
    "status": "triggered",
    "priority": 8,
    "estimated_completion": "2024-01-15T10:32:00Z"
  }
}
```

---

## 💾 **Memory Endpoints**

### **Conversation Memory**

#### **Store Conversation**
```http
POST /api/memory/conversations
Authorization: Bearer your-token
Content-Type: application/json

{
  "user_message": "How to implement user authentication?",
  "assistant_message": "Here's how to implement authentication with JWT tokens...",
  "context": {
    "domain": "web_development",
    "framework": "FastAPI"
  },
  "metadata": {
    "success": true,
    "confidence": 0.9
  }
}
```

**Response:**
```json
{
  "success": true,
  "conversation": {
    "id": "conv_123",
    "user_message": "How to implement user authentication?",
    "assistant_message": "Here's how to implement authentication with JWT tokens...",
    "context": {
      "domain": "web_development",
      "framework": "FastAPI"
    },
    "metadata": {
      "success": true,
      "confidence": 0.9
    },
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

#### **Search Conversations**
```http
GET /api/memory/conversations/search?query=authentication&max_results=10&filters[domain]=web_development
Authorization: Bearer your-token
```

**Response:**
```json
{
  "success": true,
  "conversations": [
    {
      "id": "conv_123",
      "user_message": "How to implement user authentication?",
      "assistant_message": "Here's how to implement authentication with JWT tokens...",
      "context": {
        "domain": "web_development",
        "framework": "FastAPI"
      },
      "metadata": {
        "success": true,
        "confidence": 0.9
      },
      "timestamp": "2024-01-15T10:30:00Z",
      "relevance_score": 0.95
    }
  ],
  "total_results": 1,
  "search_time": 0.05
}
```

#### **Get Conversation by ID**
```http
GET /api/memory/conversations/{conversation_id}
Authorization: Bearer your-token
```

**Response:**
```json
{
  "success": true,
  "conversation": {
    "id": "conv_123",
    "user_message": "How to implement user authentication?",
    "assistant_message": "Here's how to implement authentication with JWT tokens...",
    "context": {
      "domain": "web_development",
      "framework": "FastAPI"
    },
    "metadata": {
      "success": true,
      "confidence": 0.9
    },
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### **Memory Statistics**

#### **Get Memory Statistics**
```http
GET /api/memory/statistics
Authorization: Bearer your-token
```

**Response:**
```json
{
  "success": true,
  "statistics": {
    "total_conversations": 1250,
    "memory_usage": 45.8,
    "compression_ratio": 0.65,
    "search_accuracy": 0.92,
    "retrieval_speed": 0.05,
    "index_size": 1024,
    "last_updated": "2024-01-15T10:30:00Z"
  }
}
```

---

## 🔧 **Tool Endpoints**

### **Tool Execution**

#### **Execute Tool**
```http
POST /api/tools/execute
Authorization: Bearer your-token
Content-Type: application/json

{
  "tool_name": "think",
  "parameters": {
    "question": "How to implement user authentication?",
    "steps": ["analyze_requirements", "choose_method", "implement"]
  },
  "context": {
    "domain": "web_development"
  }
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "tool_name": "think",
    "output": "Here's a step-by-step approach to implement user authentication...",
    "execution_time": 1.2,
    "cost": 0.01,
    "confidence": 0.9,
    "metadata": {
      "steps_completed": 3,
      "reasoning_depth": "deep"
    }
  }
}
```

#### **Get Available Tools**
```http
GET /api/tools/available
Authorization: Bearer your-token
```

**Response:**
```json
{
  "success": true,
  "tools": [
    {
      "name": "think",
      "description": "Advanced reasoning tool for step-by-step problem solving",
      "category": "reasoning",
      "version": "1.0.0",
      "parameters": {
        "question": {
          "type": "string",
          "description": "Question to think about",
          "required": true
        },
        "steps": {
          "type": "array",
          "description": "Optional reasoning steps",
          "required": false
        }
      }
    },
    {
      "name": "bash",
      "description": "Execute bash commands",
      "category": "execution",
      "version": "1.0.0",
      "parameters": {
        "command": {
          "type": "string",
          "description": "Bash command to execute",
          "required": true
        }
      }
    }
  ]
}
```

#### **Get Tool Performance**
```http
GET /api/tools/performance/{tool_name}
Authorization: Bearer your-token
```

**Response:**
```json
{
  "success": true,
  "performance": {
    "tool_name": "think",
    "total_executions": 150,
    "success_rate": 0.92,
    "average_execution_time": 1.2,
    "average_cost": 0.01,
    "error_rate": 0.08,
    "optimization_improvement": 0.15
  }
}
```

---

## 📈 **Monitoring Endpoints**

### **System Status**

#### **Get System Status**
```http
GET /api/monitoring/status
Authorization: Bearer your-token
```

**Response:**
```json
{
  "success": true,
  "status": {
    "overall": "healthy",
    "components": {
      "database": "healthy",
      "llm": "healthy",
      "memory": "healthy",
      "optimization": "healthy",
      "websocket": "healthy"
    },
    "uptime": 86400,
    "version": "2.2.0",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

#### **Get System Metrics**
```http
GET /api/monitoring/metrics
Authorization: Bearer your-token
```

**Response:**
```json
{
  "success": true,
  "metrics": {
    "cpu_usage": 45.2,
    "memory_usage": 60.8,
    "disk_usage": 35.5,
    "network_io": 1024,
    "active_connections": 25,
    "requests_per_second": 15.5,
    "average_response_time": 0.25,
    "error_rate": 0.02
  }
}
```

### **Health Checks**

#### **Get Health Check**
```http
GET /api/monitoring/health
Authorization: Bearer your-token
```

**Response:**
```json
{
  "success": true,
  "health": {
    "status": "healthy",
    "checks": [
      {
        "name": "database",
        "status": "healthy",
        "response_time": 0.05,
        "last_check": "2024-01-15T10:30:00Z"
      },
      {
        "name": "llm",
        "status": "healthy",
        "response_time": 0.12,
        "last_check": "2024-01-15T10:30:00Z"
      },
      {
        "name": "memory",
        "status": "healthy",
        "response_time": 0.08,
        "last_check": "2024-01-15T10:30:00Z"
      }
    ]
  }
}
```

---

## 🎯 **WebSocket Endpoints**

### **WebSocket Connection (Socket.IO)**
```javascript
import { io } from 'socket.io-client';

// Connect to Socket.IO
const socket = io('http://localhost:3000', {
  path: '/socket.io',
  query: {
    conversationId: 'conv_123abc',
    session_api_key: 'your-session-key' // Optional
  },
  transports: ['websocket', 'polling']
});

// Listen for events
socket.on('connect', () => {
  console.log('Connected to WebSocket');
});

socket.on('disconnect', () => {
  console.log('Disconnected from WebSocket');
});
```

### **WebSocket Events**

#### **Agent Events**
```javascript
// Listen for agent responses
socket.on('agent_response', (data) => {
  console.log('Agent response:', data);
});

// Listen for agent status updates
socket.on('agent_status', (data) => {
  console.log('Agent status:', data);
});

// Send agent request
socket.emit('run_agent', {
  prompt: 'Create a user authentication system',
  context: { domain: 'web_development' }
});
```

#### **Optimization Events**
```javascript
// Listen for optimization updates
socket.on('optimization_update', (data) => {
  console.log('Optimization update:', data);
});

// Listen for performance metrics
socket.on('performance_metrics', (data) => {
  console.log('Performance metrics:', data);
});

// Trigger optimization
socket.emit('trigger_optimization', {
  prompt_id: 'system_prompt_1',
  priority: 8,
  context: { reason: 'performance_drop' }
});
```

#### **Memory Events**
```javascript
// Listen for memory updates
socket.on('memory_update', (data) => {
  console.log('Memory update:', data);
});

// Listen for conversation updates
socket.on('conversation_update', (data) => {
  console.log('Conversation update:', data);
});

// Store conversation
socket.emit('store_conversation', {
  user_message: 'How to implement authentication?',
  assistant_message: 'Here is how to implement authentication...',
  context: { domain: 'web_development' }
});
```

---

## 🔍 **Error Handling**

### **Error Response Format**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "prompt",
      "issue": "Field is required"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123"
  }
}
```

### **HTTP Status Codes**
- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request parameters
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Access denied
- **404 Not Found**: Resource not found
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error

### **Error Codes**
- **VALIDATION_ERROR**: Invalid request parameters
- **AUTHENTICATION_ERROR**: Authentication failed
- **AUTHORIZATION_ERROR**: Access denied
- **RATE_LIMIT_ERROR**: Rate limit exceeded
- **RESOURCE_NOT_FOUND**: Resource not found
- **INTERNAL_ERROR**: Internal server error
- **SERVICE_UNAVAILABLE**: Service temporarily unavailable

---

## 📚 **Examples**

### **Example 1: Complete Agent Workflow**
```bash
# 1. Create conversation
curl -X POST http://localhost:3000/api/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "https://github.com/user/repo",
    "git_provider": "github",
    "initial_user_msg": "Create a user authentication system"
  }'

# 2. Start agent loop
curl -X POST http://localhost:3000/api/conversations/{conversation_id}/start \
  -H "Content-Type: application/json" \
  -d '{
    "providers_set": ["github"]
  }'

# 3. Check conversation status
curl -X GET http://localhost:3000/api/conversations/{conversation_id}
```

### **Example 2: Memory Management**
```bash
# 1. Store memory
curl -X POST http://localhost:3000/api/memory \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "How to implement authentication?",
    "assistant_message": "Here is how to implement authentication...",
    "context": {"domain": "web_development"}
  }'

# 2. Search memory
curl -X POST http://localhost:3000/api/memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "authentication",
    "max_results": 10
  }'

# 3. Get memory statistics
curl -X GET http://localhost:3000/api/memory/stats
```

### **Example 3: Optimization Management**
```bash
# 1. Get optimization status
curl -X GET http://localhost:3000/api/prompt-optimization/status

# 2. Trigger optimization (evolve prompt)
curl -X POST http://localhost:3000/api/prompt-optimization/prompts/{prompt_id}/evolve \
  -H "Content-Type: application/json" \
  -d '{
    "priority": 8,
    "context": {"reason": "performance_drop"}
  }'

# 3. Get performance metrics
curl -X GET http://localhost:3000/api/prompt-optimization/prompts/{prompt_id}/metrics
```

---

**REST API Reference - The gateway to Forge platform.** 🌐
give 