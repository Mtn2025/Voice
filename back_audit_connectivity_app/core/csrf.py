"""
CSRF Protection Module

Provides CSRF token generation and validation for form submissions.
Works in conjunction with session middleware.
"""
import secrets

from fastapi import HTTPException, Request, status


def generate_csrf_token() -> str:
    """
    Generate cryptographically secure CSRF token.

    Returns:
        URL-safe token string
    """
    return secrets.token_urlsafe(32)


def set_csrf_token(request: Request) -> str:
    """
    Generate and store CSRF token in session.

   Args:
        request: FastAPI request object with session

    Returns:
        Generated CSRF token
    """
    token = generate_csrf_token()
    request.session["csrf_token"] = token
    return token


def get_csrf_token(request: Request) -> str | None:
    """
    Retrieve CSRF token from session.

    Args:
        request: FastAPI request object with session

    Returns:
        CSRF token if exists, None otherwise
    """
    return request.session.get("csrf_token")


def validate_csrf_token(request: Request, token: str) -> bool:
    """
    Validate CSRF token against session token.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        request: FastAPI request object with session
        token: Token to validate

    Returns:
        True if valid, False otherwise
    """
    session_token = request.session.get("csrf_token")

    if not session_token:
        return False

    # Constant-time comparison (timing attack resistant)
    return secrets.compare_digest(token, session_token)


def require_csrf_token(request: Request, submitted_token: str | None = None) -> None:
    """
    Validate CSRF token or raise HTTPException.

    Token can be in:
    - X-CSRF-Token header
    - csrf_token form field
    - submitted_token parameter

    Args:
        request: FastAPI request object
        submitted_token: Optional token to validate

    Raises:
        HTTPException: 403 if token invalid or missing
    """
    # Try multiple sources for token
    if not submitted_token:
        # Check header first
        submitted_token = request.headers.get("X-CSRF-Token")

    if not submitted_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing. Include X-CSRF-Token header or csrf_token form field."
        )

    if not validate_csrf_token(request, submitted_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token."
        )


# Dependency for route protection
async def csrf_protect(request: Request) -> None:
    """
    FastAPI dependency for CSRF protection.

    Usage:
        @router.post("/sensitive", dependencies=[Depends(csrf_protect)])
        async def sensitive_endpoint():
            ...

    Args:
        request: FastAPI request

    Raises:
        HTTPException: If CSRF validation fails
    """
    # Only validate on state-changing methods
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        # Get token from form or header
        token = request.headers.get("X-CSRF-Token")

        # Try to get from form data if header not present
        if not token:
            try:
                form = await request.form()
                token = form.get("csrf_token")
            except Exception:
                pass

        require_csrf_token(request, token)
