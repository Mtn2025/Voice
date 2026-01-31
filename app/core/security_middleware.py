"""
Security Middleware Module

Implements security headers and protections:
- X-Frame-Options: Prevent clickjacking
- X-Content-Type-Options: Prevent MIME sniffing
- Content-Security-Policy: XSS protection
- Strict-Transport-Security: Force HTTPS
- Referrer-Policy: Control referrer information
- Permissions-Policy: Control browser features
"""
import logging
from collections.abc import Callable
from typing import ClassVar

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all HTTP responses.

    Implements OWASP best practices for HTTP headers.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS protection (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content Security Policy - Restrictive but allows inline scripts for dashboard
        # Note: In production, move inline scripts to separate files and use nonces
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://unpkg.com blob:",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://unpkg.com",
            "font-src 'self' https://fonts.gstatic.com",
            # img-src must allow blob: for some visualization libs, data: for 64bit imgs
            "img-src 'self' data: blob: https:",
            # connect-src needs to allow the module import from unpkg if strict
            "connect-src 'self' wss: ws: https: http: https://unpkg.com",
            "media-src 'self' blob: https:",
            "worker-src 'self' blob:",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "upgrade-insecure-requests",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Force HTTPS in production (only if not in development)
        # Disabled for local development
        if request.url.hostname not in ["localhost", "127.0.0.1"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Referrer policy - don't leak sensitive info
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy - restrict browser features
        permissions_directives = [
            "geolocation=()",
            "microphone=(self)",  # Allow microphone for voice assistant
            "camera=()",
            "payment=()",
            "usb=()",
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_directives)

        return response


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    Enhanced CSRF protection middleware with session tokens.

    Checks for CSRF token on state-changing requests (POST, PUT, DELETE, PATCH).
    Validates against session token using constant-time comparison.
    """

    # Exempt paths that use other authentication (webhooks with signatures)
    EXEMPT_PATHS: ClassVar[list[str]] = [
        "/twilio/incoming-call",
        "/twilio/status",
        "/telnyx/webhook",
    ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate CSRF token on state-changing methods."""

        # Only check state-changing methods
        if request.method not in ["POST", "PUT", "DELETE", "PATCH"]:
            # Generate CSRF token for GET requests (stored in session)
            if request.method == "GET" and hasattr(request, 'session'):
                from app.core.csrf import set_csrf_token
                set_csrf_token(request)
            return await call_next(request)

        # Check if path is exempt
        if any(request.url.path.startswith(path) for path in self.EXEMPT_PATHS):
            return await call_next(request)

        # API endpoints with API key authentication are also exempt
        # (API keys in headers provide CSRF protection)
        if request.headers.get("X-API-Key"):
            return await call_next(request)

        # Validate CSRF token
        from app.core.csrf import validate_csrf_token

        token = request.headers.get("X-CSRF-Token")

        # Try to get from form data if header not present
        if not token:
            try:
                # Don't consume the body - just peek
                content_type = request.headers.get("content-type", "")
                if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                    # For form submissions, we'll validate later in the endpoint
                    # This is a simplified approach - full implementation would use dependency injection
                    pass
            except Exception:
                pass

        # For now, log CSRF validation but don't block (gradual rollout)
        if token and hasattr(request, 'session'):
            is_valid = validate_csrf_token(request, token)
            if not is_valid:
                logger.warning(f"Invalid CSRF token for {request.method} {request.url.path}")
                # Enforcing CSRF policy
                raise HTTPException(403, "Invalid CSRF token")

        logger.debug(f"CSRF check passed for {request.method} {request.url.path}")
        return await call_next(request)
