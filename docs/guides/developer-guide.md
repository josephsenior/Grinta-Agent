# Developer Guide - Forge Backend

This guide provides comprehensive information for developers working on the Forge backend.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Adding New Endpoints](#adding-new-endpoints)
- [Adding New Middleware](#adding-new-middleware)
- [Working with Authentication](#working-with-authentication)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Debugging](#debugging)
- [Performance Optimization](#performance-optimization)

## Architecture Overview

### Core Components

1. **FastAPI Application** (`forge/server/app.py`)
   - Main application factory
   - Middleware pipeline
   - Route registration

2. **Socket.IO Server** (`forge/server/listen_socket.py`)
   - Real-time communication
   - Event streaming
   - Connection management

3. **Conversation Manager** (`forge/server/conversation_manager/`)
   - Conversation lifecycle
   - Agent loop management
   - Session handling

4. **Runtime** (`forge/runtime/`)
   - Docker container management
   - Action execution
   - Sandbox isolation

### Request Flow

```
Client Request
    ↓
CORS Middleware
    ↓
Authentication Middleware (if enabled)
    ↓
Request ID Middleware
    ↓
Request Tracing Middleware
    ↓
Versioning Middleware
    ↓
Compression Middleware
    ↓
Security Headers Middleware
    ↓
CSRF Protection
    ↓
Resource Quota Middleware
    ↓
Rate Limiting Middleware
    ↓
Route Handler
    ↓
Response
```

## Adding New Endpoints

### 1. Create Route File

Create a new file in `forge/server/routes/`:

```python
"""Your feature routes."""

from fastapi import APIRouter, Request, HTTPException
from forge.server.utils.responses import success, error

router = APIRouter(prefix="/api/your-feature", tags=["your-feature"])

@router.get("/items")
async def get_items(request: Request):
    """Get items."""
    try:
        items = await fetch_items()
        return success(data=items, request=request)
    except Exception as e:
        return error(
            message="Failed to fetch items",
            error_code="FETCH_ITEMS_ERROR",
            request=request,
            status_code=500
        )
```

### 2. Register Router

Add to `forge/server/app.py`:

```python
from forge.server.routes.your_feature import router as your_feature_router

app.include_router(your_feature_router)
```

### 3. Use Standardized Responses

Always use `success()` and `error()` from `forge/server/utils/responses.py`:

```python
from forge.server.utils.responses import success, error

# Success response
return success(
    data={"key": "value"},
    message="Operation successful",
    request=request
)

# Error response
return error(
    message="Something went wrong",
    error_code="ERROR_CODE",
    details={"field": "error details"},
    request=request,
    status_code=400
)
```

## Adding New Middleware

### 1. Create Middleware Class

```python
"""Your middleware."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class YourMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Pre-processing
        # ...
        
        response = await call_next(request)
        
        # Post-processing
        # ...
        
        return response
```

### 2. Register Middleware

Add to `forge/server/app.py` in the correct order:

```python
from forge.server.middleware.your_middleware import YourMiddleware

app.add_middleware(YourMiddleware)
```

**Important**: Middleware order matters! See the request flow above.

## Working with Authentication

### Enable Authentication

```bash
export AUTH_ENABLED=true
export JWT_SECRET=your-secret-key
```

### Protect Endpoints

```python
from forge.server.middleware.auth import require_auth, get_current_user_id

@router.get("/protected")
async def protected_endpoint(request: Request):
    # Require authentication (raises 401 if not authenticated)
    user_id = require_auth(request)
    
    # Or get user ID (returns None if not authenticated)
    user_id = get_current_user_id(request)
    if not user_id:
        return error(message="Authentication required", request=request, status_code=401)
    
    # Your logic here
    return success(data={"user_id": user_id}, request=request)
```

### Create Tokens

```python
from forge.server.middleware.auth import AuthMiddleware, UserRole

token = AuthMiddleware.create_token(
    user_id="user123",
    email="user@example.com",
    role=UserRole.USER
)
```

## Error Handling

### Standardized Error Responses

All errors should use the `error()` helper:

```python
from forge.server.utils.responses import error

# Validation error
return error(
    message="Invalid input",
    error_code="VALIDATION_ERROR",
    details={"field": "email", "reason": "Invalid format"},
    request=request,
    status_code=400
)

# Not found
return error(
    message="Resource not found",
    error_code="NOT_FOUND",
    request=request,
    status_code=404
)

# Server error
return error(
    message="Internal server error",
    error_code="INTERNAL_ERROR",
    request=request,
    status_code=500
)
```

### Error Codes

Use consistent error codes:
- `VALIDATION_ERROR` - Input validation failed
- `AUTHENTICATION_REQUIRED` - Authentication needed
- `AUTHORIZATION_FAILED` - Insufficient permissions
- `NOT_FOUND` - Resource not found
- `RATE_LIMIT_EXCEEDED` - Rate limit exceeded
- `RESOURCE_QUOTA_EXCEEDED` - Resource quota exceeded
- `INTERNAL_ERROR` - Server error

## Testing

### Unit Tests

```python
import pytest
from fastapi.testclient import TestClient
from forge.server.app import app

client = TestClient(app)

def test_endpoint():
    response = client.get("/api/your-feature/items")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_conversation_flow():
    # Test full conversation flow
    # ...
    pass
```

## Debugging

### Enable Debug Logging

```bash
export DEBUG=true
export LOG_LEVEL=debug
```

### Request Tracing

All requests have a unique `X-Request-ID` header. Use it to trace requests:

```bash
curl -H "X-Request-ID: my-request-id" http://localhost:3000/api/endpoint
```

### Logging

```python
from forge.core.logger import forge_logger as logger

logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)  # Include stack trace
logger.debug("Debug message")
```

## Performance Optimization

### Caching

Use the caching utilities:

```python
from forge.server.utils.cache import cached, get, set

# Decorator caching
@cached("user_profile", ttl=600)
async def get_user_profile(user_id: str):
    # Expensive operation
    return await fetch_user_profile(user_id)

# Manual caching
set("key", value, ttl=300)
value = get("key")
```

### Database Queries

Use connection pooling:

```python
from forge.storage.db_pool import get_db_pool

pool = get_db_pool()
async with pool.get_connection() as conn:
    # Use connection
    pass
```

### Retry Logic

Use retry utilities for external calls:

```python
from forge.server.utils.retry import retry_async, RetryConfig

config = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    exponential_base=2.0
)

result = await retry_async(external_api_call, arg1, config=config)
```

## Best Practices

1. **Always use type hints**
2. **Use standardized responses** (`success()` and `error()`)
3. **Include request ID in responses**
4. **Handle errors gracefully**
5. **Log important events**
6. **Use async/await for I/O operations**
7. **Validate input using validation utilities**
8. **Use caching for expensive operations**
9. **Follow existing code patterns**
10. **Write tests for new features**

## Common Patterns

### Pagination

```python
from forge.server.utils.pagination import PaginatedResponse, parse_pagination_params

@router.get("/items")
async def get_items(request: Request, page: int = 1, limit: int = 20):
    params = parse_pagination_params(page=page, limit=limit)
    items, total = await fetch_items_paginated(params.offset, params.limit)
    
    return PaginatedResponse.create(
        items=items,
        page=params.page,
        limit=params.limit,
        total=total
    )
```

### Input Validation

```python
from forge.server.utils.input_validation import validate_file_path, ValidationError

@router.post("/upload")
async def upload_file(request: Request, file_path: str):
    try:
        safe_path = validate_file_path(file_path, base_dir="/workspace")
        # Process file
    except ValidationError as e:
        return error(
            message=str(e),
            error_code="VALIDATION_ERROR",
            request=request,
            status_code=400
        )
```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Socket.IO Documentation](https://socket.io/docs/v4/)
- [Forge Architecture](./architecture.md)
- [API Reference](./api-reference.md)

