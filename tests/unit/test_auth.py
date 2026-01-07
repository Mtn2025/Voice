"""
Tests unitarios para módulo de autenticación.
"""
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.core.auth_simple import generate_api_key, verify_api_key


@pytest.mark.unit
class TestAuthentication:
    """Tests para verify_api_key."""

    @patch('app.core.auth_simple.settings')
    def test_valid_credentials(self, mock_settings):
        """Test: API Key válida retorna True."""
        # Mock settings
        mock_settings.ADMIN_API_KEY = "valid-test-key-12345"

        # Simular header con key correcta
        result = verify_api_key("valid-test-key-12345")

        assert result is True

    @patch('app.core.auth_simple.settings')
    def test_invalid_api_key(self, mock_settings):
        """Test: API Key incorrecta lanza 401."""
        mock_settings.ADMIN_API_KEY = "valid-key"

        with pytest.raises(HTTPException) as exc_info:
            verify_api_key("wrong-key")

        assert exc_info.value.status_code == 401
        assert "Invalid API Key" in exc_info.value.detail

    @patch('app.core.auth_simple.settings')
    def test_missing_api_key_header(self, mock_settings):
        """Test: Header faltante lanza 401."""
        mock_settings.ADMIN_API_KEY = "valid-key"

        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(None)

        assert exc_info.value.status_code == 401
        assert "Missing X-API-Key header" in exc_info.value.detail

    @patch('app.core.auth_simple.settings')
    def test_api_key_not_configured(self, mock_settings):
        """Test: API Key no configurada lanza 503."""
        mock_settings.ADMIN_API_KEY = None

        with pytest.raises(HTTPException) as exc_info:
            verify_api_key("any-key")

        assert exc_info.value.status_code == 503
        assert "not configured" in exc_info.value.detail

    def test_generate_api_key_length(self):
        """Test: API Key generada tiene longitud apropiada."""
        key = generate_api_key(32)

        # URL-safe base64 de 32 bytes produce ~43 chars
        assert len(key) >= 40
        assert len(key) <= 50

    def test_generate_api_key_uniqueness(self):
        """Test: API Keys generadas son únicas."""
        key1 = generate_api_key()
        key2 = generate_api_key()

        assert key1 != key2

    def test_generate_api_key_url_safe(self):
        """Test: API Key usa caracteres URL-safe."""
        key = generate_api_key()

        # Caracteres URL-safe: A-Z, a-z, 0-9, -, _
        import re
        assert re.match(r'^[A-Za-z0-9_-]+$', key)
