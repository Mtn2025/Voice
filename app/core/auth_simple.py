"""
Autenticación simple con API Key para desarrollo.
Será reemplazado por sistema completo de usuarios en Etapa 2.
"""
import logging
import secrets

from fastapi import Header, Query, HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


def verify_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    api_key_query: str | None = Query(None, alias="api_key")
) -> bool:
    """
    Verifica API Key del header X-API-Key o Query param 'api_key'.

    Args:
        x_api_key: API Key del header HTTP
        api_key_query: API Key del query param (para acceso navegador)

    Returns:
        True si es válida

    Raises:
        HTTPException: 401 si falta o es inválida
    """
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

    logger.info("API Key validated successfully")
    return True


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
