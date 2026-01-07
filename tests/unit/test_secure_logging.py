"""
Tests unitarios para sistema de logging seguro.
"""
import pytest

from app.core.secure_logging import (
    get_secure_logger,
    mask_secret,
    sanitize_dict,
    sanitize_log_message,
)


@pytest.mark.unit
class TestSecureLogging:
    """Tests para sanitización de logs y protección de secrets."""

    def test_sanitize_api_key_pattern(self):
        """Test: Sanitiza patrones de API keys."""
        message = "Connecting with api_key=sk-1234567890abcdef"
        result = sanitize_log_message(message)

        assert "sk-1234567890abcdef" not in result
        assert "api_key=***" in result

    def test_sanitize_bearer_token(self):
        """Test: Sanitiza Bearer tokens."""
        message = "Authorization: Bearer abc123def456"
        result = sanitize_log_message(message)

        assert "abc123def456" not in result
        assert "***" in result  # Token sanitizado

    def test_sanitize_password_pattern(self):
        """Test: Sanitiza passwords."""
        message = "password=mySecretPass123"
        result = sanitize_log_message(message)

        assert "mySecretPass123" not in result
        assert "password=***" in result

    def test_mask_secret_short(self):
        """Test: Enmascara secret mostrando primeros caracteres."""
        secret = "sk-1234567890abcdef"
        masked = mask_secret(secret, show_chars=4)

        assert masked == "sk-1***"
        assert len(masked) < len(secret)

    def test_mask_secret_empty(self):
        """Test: Secret vacío retorna ***."""
        assert mask_secret("") == "***"
        assert mask_secret(None) == "***"

    def test_sanitize_dict_with_api_key(self):
        """Test: Sanitiza diccionario con API keys."""
        data = {
            "username": "admin",
            "api_key": "sk-1234567890",
            "timeout": 30
        }

        result = sanitize_dict(data)

        assert result["username"] == "admin"
        assert result["api_key"] == "***"
        assert result["timeout"] == 30

    def test_sanitize_dict_nested(self):
        """Test: Sanitiza diccionario anidado."""
        data = {
            "config": {
                "database_password": "secret123",
                "port": 5432
            },
            "name": "app"
        }

        result = sanitize_dict(data)

        assert result["config"]["database_password"] == "***"
        assert result["config"]["port"] == 5432
        assert result["name"] == "app"

    def test_sanitize_dict_multiple_secrets(self):
        """Test: Sanitiza múltiples secrets en dict."""
        data = {
            "azure_speech_key": "key123",
            "groq_api_key": "gsk_456",
            "telnyx_api_key": "tk_789",
            "admin_api_key": "admin_000",
            "normal_value": "not_secret"
        }

        result = sanitize_dict(data)

        # Verificar que los secrets están enmascarados
        assert result["azure_speech_key"] == "***"
        assert result["groq_api_key"] == "***"
        assert result["telnyx_api_key"] == "***"
        assert result["admin_api_key"] == "***"
        assert result["normal_value"] == "not_secret"

    def test_get_secure_logger(self):
        """Test: get_secure_logger retorna logger configurado."""
        logger = get_secure_logger("test_logger")

        assert logger is not None
        assert logger.name == "test_logger"
        assert len(logger.handlers) > 0

    def test_sanitize_preserves_safe_content(self):
        """Test: Contenido seguro no se modifica."""
        safe_message = "User logged in successfully from IP 192.168.1.1"
        result = sanitize_log_message(safe_message)

        assert result == safe_message
