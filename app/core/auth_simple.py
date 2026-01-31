"""
Autenticación simple con API Key para desarrollo.
Será reemplazado por sistema completo de usuarios en Etapa 2.
"""
import logging
import secrets

from fastapi import Header, HTTPException, Query, Request, status

from app.core.config import settings

logger = logging.getLogger(__name__)


def verify_api_key(
    request: Request,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    api_key_query: str | None = Query(None, alias="api_key")
) -> bool:
    """
    Verifica API Key del header X-API-Key o Query param 'api_key'.
    TAMBIÉN acepta autenticación por Sesión (Cookie) si existe.
    """
    # 0. Check Session (Cookie) for Dashboard Users
    if request.session.get("authenticated") is True:
        return True

    # Priorizar Header, luego Query
    api_key_to_check = x_api_key or api_key_query

    # Obtener API Key de configuración (Coolify)
    valid_key = getattr(settings, 'ADMIN_API_KEY', None)

    if not valid_key:
        logger.error("ADMIN_API_KEY not configured in environment")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API Key not configured. Contact system administrator."
        )

    if not api_key_to_check:
        logger.warning("API Key missing in request headers and query params")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key. Use header 'X-API-Key' or query param '?api_key='",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    # Comparación segura contra timing attacks
    is_valid = secrets.compare_digest(api_key_to_check, valid_key)

    if not is_valid:
        logger.warning(f"Invalid API Key attempt: {api_key_to_check[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key. Access denied.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    logger.debug("API Key validated successfully")
    return True


async def verify_dashboard_access(
    request: Request,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    api_key_query: str | None = Query(None, alias="api_key")
):
    """
    Dependency for Dashboard Access (Browser friendly).
    Checks Session -> API Key -> Redirects to Login if failed.
    """
    # 1. Check Session (Cookie)
    if request.session.get("authenticated") is True:
        return True

    # 2. Check API Key (Header/Query)
    api_key_to_check = x_api_key or api_key_query
    valid_key = getattr(settings, 'ADMIN_API_KEY', None)

    if api_key_to_check and valid_key and secrets.compare_digest(api_key_to_check, valid_key):
        # Valid Key found in request, allow pass
        return True

    # 3. Failed - Redirect if Browser
    accept = request.headers.get("Accept", "")
    if "text/html" in accept:
        # Redirect browser clients to login page using HTTP 303 See Other
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"}
        )

    # 4. API Client - Return 401
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or Invalid authentication",
        headers={"WWW-Authenticate": "ApiKey"}
    )


def generate_api_key(length: int = 32) -> str:
    """
    Genera una API Key segura para uso en configuración.

    Args:
        length: Longitud de la key en bytes (default 32)

    Returns:
        API Key en formato URL-safe base64
    """
    return secrets.token_urlsafe(length)


if __name__ == "__main__":
    # Permite generar keys desde CLI
    print("Generated API Key:")
    print(generate_api_key())
