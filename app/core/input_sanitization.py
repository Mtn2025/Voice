"""
Input Sanitization Module - Punto A5

This module provides input sanitization and validation utilities to protect against:
- XSS (Cross-Site Scripting) attacks
- SQL Injection (defense-in-depth, ORM already protects)
- Command Injection
- Path Traversal
- HTML Injection

All user inputs should be sanitized before processing or rendering.
"""

import html
import re
from typing import Any, Optional
from urllib.parse import quote, unquote

from markupsafe import Markup, escape


def sanitize_html(text: str, allow_safe_tags: bool = False) -> str:
    """
    Sanitize HTML to prevent XSS attacks.
    
    Args:
        text: Input text that may contain HTML
        allow_safe_tags: If True, allows basic safe tags like <b>, <i>, <p>
        
    Returns:
        Sanitized string safe for HTML rendering
        
    Example:
        >>> sanitize_html("<script>alert('xss')</script>")
        "&lt;script&gt;alert('xss')&lt;/script&gt;"
    """
    if not text:
        return ""
    
    # Escape all HTML entities
    sanitized = html.escape(text, quote=True)
    
    if allow_safe_tags:
        # Allow only safe tags (basic formatting)
        safe_tags = ['b', 'i', 'em', 'strong', 'p', 'br']
        for tag in safe_tags:
            # Re-allow safe tags
            sanitized = sanitized.replace(f'&lt;{tag}&gt;', f'<{tag}>')
            sanitized = sanitized.replace(f'&lt;/{tag}&gt;', f'</{tag}>')
    
    return sanitized


def sanitize_string(text: str, max_length: Optional[int] = None, allow_newlines: bool = True) -> str:
    """
    Sanitize generic string input.
    
    Removes:
    - Control characters
    - Null bytes
    - Excessive whitespace
    
    Args:
        text: Input string
        max_length: Maximum allowed length (truncate if exceeded)
        allow_newlines: If False, removes \n and \r
        
    Returns:
        Sanitized string
    """
    if not text:
        return ""
    
    # Remove null bytes (can cause issues in C-based code)
    sanitized = text.replace('\x00', '')
    
    # Remove other control characters except newline/tab
    if not allow_newlines:
        sanitized = re.sub(r'[\x00-\x1F\x7F]', '', sanitized)
    else:
        # Keep only \n, \r, \t
        sanitized = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', sanitized)
    
    # Normalize whitespace
    sanitized = ' '.join(sanitized.split())
    
    # Truncate if needed
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.
    
    Removes:
    - Path separators (/ and \\)
    - Parent directory references (..)
    - Special characters
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename
        
    Example:
        >>> sanitize_filename("../../etc/passwd")
        "etcpasswd"
        >>> sanitize_filename("<script>alert.txt")
        "scriptalert.txt"
    """
    if not filename:
        return "unnamed"
    
    # Remove path separators and parent references
    sanitized = filename.replace('..', '').replace('/', '').replace('\\', '')
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>:"|?*\x00-\x1F]', '', sanitized)
    
    # Keep only alphanumeric, dots, dashes, underscores
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', sanitized)
    
    # Ensure it doesn't start with dot (hidden file)
    sanitized = sanitized.lstrip('.')
    
    # Fallback if empty after sanitization
    if not sanitized:
        sanitized = "unnamed"
    
    return sanitized


def sanitize_phone_number(phone: str) -> str:
    """
    Sanitize phone number input.
    
    Keeps only digits, +, and basic formatting characters.
    
    Args:
        phone: Phone number input
        
    Returns:
        Sanitized phone number
        
    Example:
        >>> sanitize_phone_number("+1 (555) 123-4567")
        "+1 (555) 123-4567"
        >>> sanitize_phone_number("<script>alert()</script>")
        ""
    """
    if not phone:
        return ""
    
    # Keep only digits, +, -, (, ), spaces
    sanitized = re.sub(r'[^0-9+\-() ]', '', phone)
    
    # Remove excessive spaces
    sanitized = ' '.join(sanitized.split())
    
    return sanitized.strip()


def sanitize_email(email: str) -> str:
    """
    Sanitize email address.
    
    Basic sanitization - full validation should be done with Pydantic EmailStr.
    
    Args:
        email: Email address
        
    Returns:
        Sanitized email (lowercase, trimmed)
    """
    if not email:
        return ""
    
    # Remove whitespace and convert to lowercase
    sanitized = email.strip().lower()
    
    # Remove any HTML/script tags
    sanitized = re.sub(r'<[^>]*>', '', sanitized)
    
    # Basic format: keep only valid email characters
    sanitized = re.sub(r'[^a-z0-9@._+-]', '', sanitized)
    
    return sanitized


def sanitize_sql_like_pattern(pattern: str) -> str:
    """
    Sanitize SQL LIKE pattern to prevent SQL injection in LIKE clauses.
    
    Even though we use ORM, this is defense-in-depth for raw SQL scenarios.
    
    Args:
        pattern: LIKE pattern
        
    Returns:
        Escaped pattern safe for SQL LIKE
    """
    if not pattern:
        return ""
    
    # Escape SQL LIKE wildcards
    sanitized = pattern.replace('\\', '\\\\')  # Escape backslash first
    sanitized = sanitized.replace('%', '\\%')  # Escape %
    sanitized = sanitized.replace('_', '\\_')  # Escape _
    
    return sanitized


def sanitize_url(url: str, allowed_schemes: Optional[list[str]] = None) -> str:
    """
    Sanitize URL to prevent javascript: and data: URL attacks.
    
    Args:
        url: URL to sanitize
        allowed_schemes: List of allowed schemes (default: ['http', 'https'])
        
    Returns:
        Sanitized URL or empty string if unsafe
        
    Example:
        >>> sanitize_url("https://example.com")
        "https://example.com"
        >>> sanitize_url("javascript:alert('xss')")
        ""
    """
    if not url:
        return ""
    
    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']
    
    # Extract scheme
    url = url.strip()
    scheme = url.split(':', 1)[0].lower() if ':' in url else ''
    
    # Reject dangerous schemes
    dangerous_schemes = ['javascript', 'data', 'vbscript', 'file']
    if scheme in dangerous_schemes:
        return ""
    
    # If scheme specified, must be in allowed list
    if scheme and scheme not in allowed_schemes:
        return ""
    
    # Basic XSS pattern detection
    xss_patterns = [
        r'<script',
        r'javascript:',
        r'onerror=',
        r'onload=',
        r'eval\(',
    ]
    
    url_lower = url.lower()
    for pattern in xss_patterns:
        if re.search(pattern, url_lower):
            return ""
    
    return url


def validate_json_input(data: dict[str, Any], max_depth: int = 10) -> dict[str, Any]:
    """
    Validate JSON input depth to prevent DoS attacks.
    
    Args:
        data: JSON data as dict
        max_depth: Maximum allowed nesting depth
        
    Returns:
        Original data if valid
        
    Raises:
        ValueError: If nesting exceeds max_depth
    """
    def get_depth(obj: Any, current_depth: int = 0) -> int:
        if current_depth > max_depth:
            raise ValueError(f"JSON input exceeds maximum depth of {max_depth}")
        
        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(get_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(get_depth(item, current_depth + 1) for item in obj)
        else:
            return current_depth
    
    get_depth(data)
    return data


def escape_for_javascript(text: str) -> str:
    """
    Escape string for safe embedding in JavaScript.
    
    Args:
        text: Text to escape
        
    Returns:
        JavaScript-safe escaped string
    """
    if not text:
        return ""
    
    # Escape JavaScript special characters
    escaped = text.replace('\\', '\\\\')  # Backslash
    escaped = escaped.replace('"', '\\"')  # Double quote
    escaped = escaped.replace("'", "\\'")  # Single quote
    escaped = escaped.replace('\n', '\\n')  # Newline
    escaped = escaped.replace('\r', '\\r')  # Carriage return
    escaped = escaped.replace('\t', '\\t')  # Tab
    escaped = escaped.replace('</script>', '<\\/script>')  # Script closing tag
    
    return escaped


# ============================================================================
# Jinja2 Template Filters (for use in templates)
# ============================================================================

def register_template_filters(app):
    """
    Register sanitization filters for Jinja2 templates.
    
    Usage in templates:
        {{ user_input | sanitize }}
        {{ user_input | sanitize_js }}
    
    Args:
        app: FastAPI/Starlette app instance
    """
    from starlette.templating import Jinja2Templates
    
    # Note: In FastAPI, templates are typically created per router
    # This function should be called where templates are initialized
    
    def template_sanitize(text: str) -> Markup:
        """Safe HTML escaping for templates."""
        return Markup(escape(text))
    
    def template_sanitize_js(text: str) -> str:
        """Safe JS escaping for templates."""
        return escape_for_javascript(str(text))
    
    # Return filters dict for manual registration
    return {
        'sanitize': template_sanitize,
        'sanitize_js': template_sanitize_js,
    }
