"""
Utilidades para logging seguro que evita la exposición de secretos.
"""
import logging
import re
from typing import Any

# Patrones para detectar secretos en logs
SECRET_PATTERNS = [
    (r'Bearer\s+[A-Za-z0-9\-._~+/]+', 'Bearer ***'),
    (r'api[_-]?key["\']?\s*[:=]\s*["\']?([A-Za-z0-9\-._~+/]+)', r'api_key=***'),
    (r'token["\']?\s*[:=]\s*["\']?([A-Za-z0-9\-._~+/]+)', r'token=***'),
    (r'password["\']?\s*[:=]\s*["\']?([^\s"\']+)', r'password=***'),
    (r'secret["\']?\s*[:=]\s*["\']?([A-Za-z0-9\-._~+/]+)', r'secret=***'),
    (r'authorization["\']?\s*[:=]\s*["\']?([^\s"\']+)', r'authorization=***'),
]

# Nombres de variables que contienen secretos
SECRET_KEYS = {
    'api_key', 'apikey', 'api-key', 'key',
    'secret', 'secret_key', 'secret-key', 'secretkey',
    'password', 'passwd', 'pwd',
    'token', 'auth_token', 'auth-token', 'authtoken',
    'authorization',
    'telnyx', 'telnyxapikey',
    'twilio', 'twilioauthtoken',
    'azure', 'azurespeech', 'azurespeechkey',
    'groq', 'groqapikey',
    'admin', 'adminapikey',
}


def sanitize_log_message(message: str) -> str:
    """
    Sanitiza un mensaje de log reemplazando secretos con placeholders.

    Args:
        message: Mensaje original del log

    Returns:
        Mensaje sanitizado sin secretos expuestos
    """
    sanitized = message

    # Aplicar patrones regex
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    return sanitized


def mask_secret(value: str, show_chars: int = 4) -> str:
    """
    Enmascara un secret mostrando solo los primeros caracteres.

    Args:
        value: Valor del secret
        show_chars: Número de caracteres a mostrar al inicio

    Returns:
        Secret enmascarado (ej: "key_***")
    """
    if not value or len(value) <= show_chars:
        return "***"

    return f"{value[:show_chars]}***"


def sanitize_dict(data: dict[str, Any], mask_keys: bool = True) -> dict[str, Any]:
    """
    Sanitiza un diccionario reemplazando valores de keys sensibles.

    Args:
        data: Diccionario a sanitizar
        mask_keys: Si True, enmascara valores; si False, los elimina

    Returns:
        Diccionario sanitizado
    """
    sanitized = {}

    for key, value in data.items():
        key_lower = key.lower().replace('_', '').replace('-', '')

        # Verificar si la key es sensible
        is_secret = any(secret_key in key_lower for secret_key in SECRET_KEYS)

        if is_secret:
            if mask_keys:
                sanitized[key] = "***"  # Siempre usar *** para secrets
            # Si mask_keys=False, simplemente no incluimos la key
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, mask_keys)
        elif isinstance(value, str):
            sanitized[key] = sanitize_log_message(value)
        else:
            sanitized[key] = value

    return sanitized


class SecureFormatter(logging.Formatter):
    """
    Formatter de logging que sanitiza mensajes automáticamente.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Sanitizar el mensaje
        original_msg = record.msg
        if isinstance(original_msg, str):
            record.msg = sanitize_log_message(original_msg)

        # Formatear normalmente
        result = super().format(record)

        # Restaurar mensaje original (por si acaso)
        record.msg = original_msg

        return result


def get_secure_logger(name: str) -> logging.Logger:
    """
    Crea un logger con sanitización automática de secretos.

    Args:
        name: Nombre del logger

    Returns:
        Logger configurado con SecureFormatter
    """
    logger = logging.getLogger(name)

    # Solo configurar si no tiene handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = SecureFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


# Logger global seguro
secure_logger = get_secure_logger('secure')


if __name__ == "__main__":
    # Tests
    print("Testing sanitization...")

    # Test 1: Sanitizar mensaje
    msg = "API Key: sk-1234567890abcdef, Token: bearer_abc123"
    print(f"Original: {msg}")
    print(f"Sanitized: {sanitize_log_message(msg)}")

    # Test 2: Mask secret
    print(f"\nMasked: {mask_secret('sk-1234567890abcdef')}")

    # Test 3: Sanitizar dict
    data = {
        "username": "admin",
        "api_key": "sk-1234567890abcdef",
        "config": {
            "password": "secret123",
            "timeout": 30
        }
    }
    print(f"\nOriginal dict: {data}")
    print(f"Sanitized dict: {sanitize_dict(data)}")
