# 🌐 **REST API Reference**

> **Comprehensive REST API documentation for the OpenHands platform, covering all endpoints, request/response formats, and authentication.**

---

## 📖 **Table of Contents**

- [🌟 Overview](#-overview)
- [🔐 Authentication](#-authentication)
- [📊 Base URLs](#-base-urls)
- [🤖 Agent Endpoints](#-agent-endpoints)
- [🎨 MetaSOP Endpoints](#-metasop-endpoints) (NEW!)
- [⚡ Optimization Endpoints](#-optimization-endpoints)
- [💾 Memory Endpoints](#-memory-endpoints)
- [🔧 Tool Endpoints](#-tool-endpoints)
- [📈 Monitoring Endpoints](#-monitoring-endpoints)
- [🎯 WebSocket Endpoints](#-websocket-endpoints)
- [🔍 Error Handling](#-error-handling)
- [📚 Examples](#-examples)

---

## 🌟 **Overview**

The OpenHands REST API provides comprehensive access to all platform features through HTTP endpoints. The API follows RESTful principles and uses JSON for data exchange.

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

### **Authentication Endpoints**
```http
# Login
POST /api/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123"
}

# Response
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "user": {
    "id": "user_123",
    "username": "user@example.com",
    "role": "user"
  }
}

# Logout
POST /api/auth/logout
Authorization: Bearer your-token

# Response
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## 📊 **Base URLs**

### **Development**
```
http://localhost:8000/api/v1
```

### **Staging**
```
https://staging-api.openhands.ai/api/v1
```

### **Production**
```
https://api.openhands.ai/api/v1
```

### **WebSocket URLs**
```
# Development
ws://localhost:8000/ws

# Staging
wss://staging-api.openhands.ai/ws

# Production
wss://api.openhands.ai/ws
```

---

## 🤖 **Agent Endpoints**

### **CodeAct Agent**

#### **Run Agent**
```http
POST /api/agent/run
Authorization: Bearer your-token
Content-Type: application/json

{
  "prompt": "Create a user authentication system",
  "context": {
    "domain": "web_development",
    "framework": "FastAPI",
    "database": "PostgreSQL"
  },
  "options": {
    "max_iterations": 10,
    "timeout": 300,
    "enable_memory": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "response": {
    "code": "from fastapi import FastAPI, Depends, HTTPException\nfrom fastapi.security import HTTPBearer\n...",
    "output": "User authentication system created successfully",
    "execution_time": 2.5,
    "memory_usage": 15.2,
    "token_usage": 1250,
    "confidence": 0.95
  },
  "metadata": {
    "agent_id": "codeact_agent_123",
    "session_id": "session_456",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

#### **Get Agent Status**
```http
GET /api/agent/status
Authorization: Bearer your-token
```

**Response:**
```json
{
  "success": true,
  "status": {
    "is_running": true,
    "active_sessions": 5,
    "total_runs": 1250,
    "success_rate": 0.92,
    "average_execution_time": 3.2,
    "memory_usage": 45.8
  }
}
```

#### **Get Agent Metrics**
```http
GET /api/agent/metrics
Authorization: Bearer your-token
```

**Response:**
```json
{
  "success": true,
  "metrics": {
    "total_runs": 1250,
    "success_rate": 0.92,
    "average_execution_time": 3.2,
    "memory_usage": 45.8,
    "token_usage": 125000,
    "error_rate": 0.08,
    "uptime": 86400
  }
}
```

### **MetaSOP Orchestrator**

#### **Execute Task** (Enhanced with Visualization Support)
```http
POST /api/metasop/execute
Authorization: Bearer your-token
Content-Type: application/json

{
  "task": {
    "title": "Implement user authentication",
    "description": "Create a complete authentication system with JWT tokens",
    "priority": "high",
    "requirements": ["security", "scalability", "user_friendly"]
  },
  "options": {
    "max_agents": 5,
    "timeout": 600,
    "enable_collaboration": true,
    "enable_visualization": true,
    "real_time_updates": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "task_id": "task_789",
    "orchestration_id": "orch_456",
    "status": "completed",
    "agents_used": ["product_manager", "architect", "engineer", "qa", "ui_designer"],
    "execution_time": 45.2,
    "files_created": ["auth.py", "models.py", "routes.py", "tests.py"],
    "tests_written": 15,
    "documentation_created": true,
    "visualization_url": "/api/metasop/orchestrations/orch_456/visualization",
    "websocket_url": "ws://localhost:8000/ws/metasop/orch_456"
  },
  "metadata": {
    "orchestrator_id": "metasop_123",
    "session_id": "session_456",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

#### **Get Task Status** (with Visualization Data)
```http
GET /api/metasop/tasks/{task_id}/status
Authorization: Bearer your-token
```

**Response:**
```json
{
  "success": true,
  "task": {
    "id": "task_789",
    "orchestration_id": "orch_456",
    "title": "Implement user authentication",
    "status": "in_progress",
    "progress": 0.75,
    "current_agent": "engineer",
    "estimated_completion": "2024-01-15T11:00:00Z",
    "agents_used": ["product_manager", "architect", "engineer"],
    "files_created": ["auth.py", "models.py"],
    "tests_written": 8,
    "steps": [
      {
        "step_id": "pm_spec",
        "role": "product_manager",
        "status": "success",
        "has_visualization": true
      },
      {
        "step_id": "architecture",
        "role": "architect",
        "status": "success",
        "has_visualization": true
      },
      {
        "step_id": "implementation",
        "role": "engineer",
        "status": "in_progress",
        "has_visualization": false
      }
    ]
  }
}
```

#### **Get Visualization Data** (NEW!)
```http
GET /api/metasop/orchestrations/{orchestration_id}/visualization
Authorization: Bearer your-token
```

**Response:**
```json
{
  "success": true,
  "visualization": {
    "orchestration_id": "orch_456",
    "flow_diagram": {
      "nodes": [
        {
          "id": "pm_spec",
          "type": "custom",
          "position": { "x": 0, "y": 0 },
          "data": {
            "role": "product_manager",
            "title": "Product Manager",
            "status": "success",
            "artifact": {
              "user_stories": [...],
              "acceptance_criteria": [...]
            }
          }
        },
        {
          "id": "architecture",
          "type": "custom",
          "position": { "x": 300, "y": 0 },
          "data": {
            "role": "architect",
            "title": "Architect",
            "status": "success",
            "artifact": {
              "architecture_diagram": "...",
              "api_endpoints": [...],
              "architectural_decisions": [...]
            }
          }
        }
      ],
      "edges": [
        {
          "id": "e1-2",
          "source": "pm_spec",
          "target": "architecture",
          "animated": true
        }
      ]
    },
    "metrics": {
      "total_steps": 4,
      "completed_steps": 2,
      "failed_steps": 0,
      "in_progress_steps": 1,
      "total_duration": 75.5,
      "success_rate": 1.0
    }
  }
}
```

#### **Get Agent Artifact** (NEW!)
```http
GET /api/metasop/orchestrations/{orchestration_id}/steps/{step_id}/artifact
Authorization: Bearer your-token
```

**Response:**
```json
{
  "success": true,
  "artifact": {
    "step_id": "pm_spec",
    "role": "product_manager",
    "type": "pm_spec",
    "data": {
      "user_stories": [
        {
          "title": "User Authentication",
          "description": "As a user, I want to login so that I can access my account",
          "priority": "high",
          "acceptance_criteria": [
            "User can enter email/password",
            "System validates credentials",
            "User redirected on success"
          ]
        }
      ],
      "acceptance_criteria": [
        { "criteria": "Secure password hashing" },
        { "criteria": "JWT token generation" }
      ]
    },
    "generated_at": "2025-01-23T10:30:45Z"
  }
}
```

### **WebSocket Events for MetaSOP** (NEW!)

MetaSOP emits real-time events via WebSocket for live visualization updates:

```javascript
// Connect to MetaSOP WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/metasop/orch_456');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  // Event types:
  // - orchestration_start: Orchestration has started
  // - step_start: Agent step started
  // - step_progress: Progress update
  // - step_complete: Agent step completed with artifact
  // - step_error: Error in step
  // - orchestration_complete: All steps completed
  
  console.log('MetaSOP Event:', data);
};
```

**Example Event (Step Complete with Visualization Data):**
```json
{
  "type": "metasop_step_update",
  "event_type": "step_complete",
  "orchestration_id": "orch_456",
  "step_id": "pm_spec",
  "role": "product_manager",
  "status": "success",
  "artifact": {
    "user_stories": [...],
    "acceptance_criteria": [...]
  },
  "timestamp": "2025-01-23T10:30:45Z",
  "duration": 45.2
}
```

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

### **WebSocket Connection**
```javascript
// Connect to WebSocket
const socket = io('ws://localhost:8000/ws', {
  auth: {
    token: 'your-jwt-token'
  }
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
# 1. Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "password": "password123"
  }'

# 2. Run agent
curl -X POST http://localhost:8000/api/agent/run \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a user authentication system",
    "context": {
      "domain": "web_development",
      "framework": "FastAPI"
    }
  }'

# 3. Check agent status
curl -X GET http://localhost:8000/api/agent/status \
  -H "Authorization: Bearer your-token"
```

### **Example 2: Memory Management**
```bash
# 1. Store conversation
curl -X POST http://localhost:8000/api/memory/conversations \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "How to implement authentication?",
    "assistant_message": "Here is how to implement authentication...",
    "context": {"domain": "web_development"}
  }'

# 2. Search conversations
curl -X GET "http://localhost:8000/api/memory/conversations/search?query=authentication&max_results=10" \
  -H "Authorization: Bearer your-token"

# 3. Get memory statistics
curl -X GET http://localhost:8000/api/memory/statistics \
  -H "Authorization: Bearer your-token"
```

### **Example 3: Optimization Management**
```bash
# 1. Get optimization status
curl -X GET http://localhost:8000/api/optimization/status \
  -H "Authorization: Bearer your-token"

# 2. Trigger optimization
curl -X POST http://localhost:8000/api/optimization/trigger \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_id": "system_prompt_1",
    "priority": 8,
    "context": {"reason": "performance_drop"}
  }'

# 3. Get performance metrics
curl -X GET http://localhost:8000/api/optimization/metrics/system_prompt_1 \
  -H "Authorization: Bearer your-token"
```

---

**REST API Reference - The gateway to OpenHands platform.** 🌐
give 