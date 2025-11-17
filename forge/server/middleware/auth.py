"""Authentication and authorization middleware for Forge API.

Provides JWT-based authentication, session management, and role-based access control.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional
from enum import Enum

import jwt
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from forge.core.logger import forge_logger as logger
from forge.server.utils.responses import error

if TYPE_CHECKING:
    from fastapi import Response

# JWT Configuration
# Note: These are read at import time for backward compatibility, but
# _get_jwt_secret() and _get_jwt_algorithm() should be used to read at runtime
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY") or "change-me-in-production"
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))


def _get_jwt_secret() -> str:
    """Get JWT secret from environment at runtime.
    
    This ensures that environment variable changes (e.g., in tests) take effect.
    """
    return os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY") or "change-me-in-production"


def _get_jwt_algorithm() -> str:
    """Get JWT algorithm from environment at runtime.
    
    This ensures that environment variable changes (e.g., in tests) take effect.
    """
    return os.getenv("JWT_ALGORITHM", "HS256")

# Security scheme
security = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    """User roles for authorization."""

    ADMIN = "admin"
    USER = "user"
    SERVICE = "service"  # For service-to-service authentication


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication and authorization.

    Public endpoints (health checks, public API) are excluded from authentication.
    Protected endpoints require a valid JWT token in the Authorization header.
    """

    # Public endpoints that don't require authentication
    PUBLIC_PATHS = {
        "/health",
        "/api/health",
        "/api/monitoring/health",
        "/alive",
        "/server_info",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/options/models",
        "/api/options/agents",
        "/api/options/security-analyzers",
        "/api/options/config",
        "/api/auth/register",  # Registration endpoint
        "/api/auth/login",  # Login endpoint
        "/api/auth/forgot-password",  # Password reset request
        "/api/auth/reset-password",  # Password reset confirmation
    }

    # Paths that require authentication but allow anonymous access
    OPTIONAL_AUTH_PATHS = {
        "/api/conversations",  # POST to create conversation
    }

    async def dispatch(self, request: Request, call_next):
        """Process request with authentication check."""
        # Skip authentication for public paths
        if request.url.path in self.PUBLIC_PATHS or request.url.path.startswith("/assets"):
            return await call_next(request)

        # Check for authentication token
        auth_header = request.headers.get("Authorization")
        token = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
        elif auth_header and auth_header.startswith("Token "):
            token = auth_header[6:]

        # For optional auth paths, allow anonymous access but set user_id to None
        if request.url.path in self.OPTIONAL_AUTH_PATHS and not token:
            request.state.user_id = None
            request.state.user_role = UserRole.USER
            return await call_next(request)

        # Validate token for protected endpoints
        if not token:
            return error(
                message="Authentication required",
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="AUTHENTICATION_REQUIRED",
                details={"path": request.url.path},
            )

        try:
            payload = self._verify_token(token)
            user_id = payload.get("user_id")
            request.state.user_id = user_id
            request.state.user_email = payload.get("email")
            request.state.user_role = UserRole(payload.get("role", "user"))
            request.state.token_payload = payload
            
            # Verify user still exists and is active (optional check, can be disabled for performance)
            verify_user_active = os.getenv("AUTH_VERIFY_USER_ACTIVE", "true").lower() == "true"
            if verify_user_active and user_id:
                try:
                    from forge.storage.user.file_user_store import get_user_store
                    user_store = get_user_store()
                    user = await user_store.get_user_by_id(user_id)
                    if not user or not user.is_active:
                        return error(
                            message="User account not found or deactivated",
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            error_code="ACCOUNT_INACTIVE",
                        )
                except Exception as e:
                    logger.warning(f"Error verifying user active status: {e}")
                    # Continue if verification fails (don't block request)
        except jwt.ExpiredSignatureError:
            return error(
                message="Token has expired",
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="TOKEN_EXPIRED",
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return error(
                message="Invalid authentication token",
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="INVALID_TOKEN",
            )
        except Exception as e:
            logger.error(f"Authentication error: {e}", exc_info=True)
            return error(
                message="Authentication failed",
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="AUTHENTICATION_ERROR",
            )

        return await call_next(request)

    @staticmethod
    def _verify_token(token: str) -> dict:
        """Verify and decode JWT token."""
        # Read from environment at runtime to support dynamic configuration (e.g., in tests)
        secret = _get_jwt_secret()
        algorithm = _get_jwt_algorithm()
        return jwt.decode(token, secret, algorithms=[algorithm])

    @staticmethod
    def create_token(
        user_id: str,
        email: Optional[str] = None,
        role: UserRole = UserRole.USER,
        expires_in_hours: Optional[int] = None,
    ) -> str:
        """Create a JWT token for a user.

        Args:
            user_id: Unique user identifier
            email: User email (optional)
            role: User role (default: USER)
            expires_in_hours: Token expiration in hours (default: JWT_EXPIRATION_HOURS)

        Returns:
            Encoded JWT token string
        """
        expiration = expires_in_hours or JWT_EXPIRATION_HOURS
        payload = {
            "user_id": user_id,
            "email": email,
            "role": role.value,
            "exp": datetime.utcnow() + timedelta(hours=expiration),
            "iat": datetime.utcnow(),
        }
        # Read from environment at runtime to support dynamic configuration (e.g., in tests)
        secret = _get_jwt_secret()
        algorithm = _get_jwt_algorithm()
        return jwt.encode(payload, secret, algorithm=algorithm)

    @staticmethod
    def require_role(required_role: UserRole):
        """Decorator to require a specific role for an endpoint."""

        async def role_checker(request: Request):
            user_role = getattr(request.state, "user_role", None)
            if not user_role or user_role != required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires {required_role.value} role",
                )
            return request

        return role_checker


def get_current_user_id(request: Request) -> Optional[str]:
    """Get the current user ID from request state."""
    return getattr(request.state, "user_id", None)


def get_current_user_role(request: Request) -> Optional[UserRole]:
    """Get the current user role from request state."""
    return getattr(request.state, "user_role", None)


def require_auth(request: Request) -> str:
    """Require authentication and return user ID.

    Raises HTTPException if user is not authenticated.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user_id

