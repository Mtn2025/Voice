"""
Autenticación simple con API Key para desarrollo.
Será reemplazado por sistema completo de usuarios en Etapa 2.
"""
import logging
import secrets

from fastapi import Header, HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


def verify_api_key(x_api_key: str | None = Header(None)) -> bool:
    """
    Verifica API Key del header X-API-Key.

    Args:
        x_api_key: API Key del header HTTP

    Returns:
        True si es válida

    Raises:
        HTTPException: 401 si falta o es inválida
    """
    # Obtener API Key de configuración (Coolify)
    valid_key = getattr(settings, 'ADMIN_API_KEY', None)

    if not valid_key:
        logger.error("ADMIN_API_KEY not configured in environment")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API Key not configured. Contact system administrator."
        )

    if not x_api_key:
        logger.warning("API Key missing in request headers")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header. Access denied.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    # Comparación segura contra timing attacks
    is_valid = secrets.compare_digest(x_api_key, valid_key)

    if not is_valid:
        logger.warning(f"Invalid API Key attempt: {x_api_key[:8]}...")
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
