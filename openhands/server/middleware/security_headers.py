"""Security headers middleware for OpenHands."""

from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse


class SecurityHeadersMiddleware:
    """Middleware to add security headers to all responses."""

    def __init__(self, enabled: bool = True) -> None:
        """Initialize security headers middleware.

        Args:
            enabled: Whether to add security headers
        """
        self.enabled = enabled

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response with security headers
        """
        response = await call_next(request)

        if not self.enabled:
            return response

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Force HTTPS in production
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Content Security Policy
        # Note: Adjust these directives based on your specific needs
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Required for Monaco, Mermaid
            "style-src 'self' 'unsafe-inline'",  # Required for Tailwind, inline styles
            "img-src 'self' data: https:",  # Allow images from data URLs and HTTPS
            "font-src 'self' data:",
            "connect-src 'self' ws: wss: https:",  # Allow WebSocket and API connections
            "frame-src 'self'",  # Allow iframes from same origin (Jupyter, served apps)
            "worker-src 'self' blob:",  # Allow web workers
            "object-src 'none'",  # Disallow plugins
            "base-uri 'self'",  # Restrict base tag
            "form-action 'self'",  # Restrict form submissions
            "frame-ancestors 'none'",  # Prevent embedding
            "upgrade-insecure-requests",  # Upgrade HTTP to HTTPS
        ]

        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Permissions Policy (formerly Feature-Policy)
        permissions_directives = [
            "camera=()",  # Disable camera
            "microphone=()",  # Disable microphone
            "geolocation=()",  # Disable geolocation
            "payment=()",  # Disable payment API
            "usb=()",  # Disable USB access
            "magnetometer=()",  # Disable magnetometer
            "gyroscope=()",  # Disable gyroscope
            "accelerometer=()",  # Disable accelerometer
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_directives)

        # Cross-Origin Policies (modern security)
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # X-Permitted-Cross-Domain-Policies (Adobe products)
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        return response


class CSRFProtection:
    """CSRF protection middleware."""

    # Methods that require CSRF protection
    PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    # Paths to skip CSRF check (e.g., webhooks with signature verification)
    SKIP_PATHS = {
        "/api/slack/events",  # Slack verifies its own signatures
        "/api/slack/callback",  # OAuth callback
    }

    def __init__(self, enabled: bool = True) -> None:
        """Initialize CSRF protection.

        Args:
            enabled: Whether CSRF protection is enabled
        """
        self.enabled = enabled

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Validate CSRF for state-changing requests.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response or CSRF error
        """
        if not self.enabled:
            return await call_next(request)

        # Skip CSRF check for safe methods
        if request.method not in self.PROTECTED_METHODS:
            return await call_next(request)

        # Skip CSRF check for excluded paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # Validate Origin/Referer headers
        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")

        # At least one of Origin or Referer must be present
        if not origin and not referer:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF validation failed: Missing Origin/Referer header"},
            )

        # Validate Origin matches host
        if origin:
            request_host = f"{request.url.scheme}://{request.url.netloc}"
            # Allow localhost development (different ports)
            if not origin.startswith(request_host) and not self._is_localhost_development(origin, request_host):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed: Origin mismatch"},
                )

        # Validate Referer matches host
        if referer:
            request_host = f"{request.url.scheme}://{request.url.netloc}"
            # Allow localhost development (different ports)
            if not referer.startswith(request_host) and not self._is_localhost_development(referer, request_host):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed: Referer mismatch"},
                )

        # CSRF check passed
        return await call_next(request)

    def _is_localhost_development(self, origin: str, request_host: str) -> bool:
        """Check if this is a localhost development scenario (different ports)."""
        try:
            from urllib.parse import urlparse
            origin_parsed = urlparse(origin)
            request_parsed = urlparse(request_host)
            
            # Both must be localhost/127.0.0.1
            origin_host = origin_parsed.hostname
            request_hostname = request_parsed.hostname
            
            is_localhost = origin_host in ('localhost', '127.0.0.1') and request_hostname in ('localhost', '127.0.0.1')
            same_scheme = origin_parsed.scheme == request_parsed.scheme
            
            return is_localhost and same_scheme
        except Exception:
            return False
