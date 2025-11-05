"""
Request Tracing Middleware

Adds correlation IDs to all requests for end-to-end tracing.

Features:
- Unique request ID per request
- Propagates through logs
- Included in responses
- Performance timing
- Distributed tracing ready
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from openhands.core.logger import openhands_logger as logger


class RequestTracingMiddleware:
    """Middleware that adds request ID and timing to all requests."""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
    
    async def __call__(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Add request ID and timing to request."""
        if not self.enabled:
            return await call_next(request)
        
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Store request ID in request state for access in route handlers
        request.state.request_id = request_id
        
        # Store in thread-local storage for logging
        import contextvars
        _request_id_ctx_var.set(request_id)
        
        # Record start time
        start_time = time.time()
        
        # Log request start
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error with request ID
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(e),
                },
                exc_info=True
            )
            raise
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        
        # Log request completion
        logger.info(
            f"Request completed: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
        )
        
        # Track slow requests
        if duration_ms > 1000:  # > 1 second
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "duration_ms": duration_ms,
                    "threshold_ms": 1000,
                }
            )
        
        return response


# Context variable for request ID (accessible in logs)
_request_id_ctx_var = contextvars.ContextVar("request_id", default=None)


def get_current_request_id() -> str | None:
    """Get the current request ID from context.
    
    Usage in route handlers:
        request_id = get_current_request_id()
        logger.info(f"Processing...", extra={"request_id": request_id})
    
    Returns:
        Request ID string or None if not in request context
    """
    return _request_id_ctx_var.get()


# Custom log filter to inject request ID into all logs
class RequestIDFilter(logging.Filter):
    """Logging filter that adds request_id to all log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request_id to log record if available."""
        request_id = _request_id_ctx_var.get()
        if request_id:
            record.request_id = request_id
        return True


# Enhanced JSON formatter with request ID
class EnhancedJSONFormatter(JsonFormatter):
    """JSON formatter that always includes request_id if available."""
    
    def add_fields(self, log_record, record, message_dict):
        """Add custom fields to JSON log output."""
        super().add_fields(log_record, record, message_dict)
        
        # Add request ID if available
        request_id = getattr(record, 'request_id', None)
        if request_id:
            log_record['request_id'] = request_id
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add thread/process info
        log_record['thread_name'] = record.threadName
        log_record['process_id'] = record.process
        
        # Add file location
        log_record['location'] = f"{record.filename}:{record.lineno}"


import contextvars
import logging
from datetime import datetime
from pythonjsonlogger.json import JsonFormatter

