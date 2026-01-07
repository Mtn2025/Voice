"""
Tests de integración para carga de configuración.
"""
import pytest

from app.core.config import Settings


@pytest.mark.integration
class TestConfigLoading:
    """Tests de carga de configuración desde variables de entorno."""

    def test_config_loads_from_env(self, monkeypatch):
        """Test: Configuración carga correctamente desde env vars."""
        # Simular variables de entorno
        monkeypatch.setenv("AZURE_SPEECH_KEY", "test-key-123")
        monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

        # Crear instancia de Settings (Pydantic recarga)
        settings = Settings()

        assert settings.AZURE_SPEECH_KEY == "test-key-123"
        assert settings.AZURE_SPEECH_REGION == "eastus"
        assert settings.GROQ_API_KEY == "test-groq-key"

    def test_config_database_url_construction(self, monkeypatch):
        """Test: DATABASE_URL se construye correctamente."""
        monkeypatch.setenv("POSTGRES_USER", "testuser")
        monkeypatch.setenv("POSTGRES_PASSWORD", "testpass")
        monkeypatch.setenv("POSTGRES_SERVER", "localhost")
        monkeypatch.setenv("POSTGRES_PORT", "5432")
        monkeypatch.setenv("POSTGRES_DB", "testdb")

        settings = Settings()

        expected_url = "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"
        assert expected_url == settings.DATABASE_URL

    def test_config_defaults(self):
        """Test: Valores por defecto se aplican correctamente."""
        settings = Settings()

        assert settings.POSTGRES_USER == "postgres"
        assert settings.POSTGRES_PASSWORD == "postgres"
        assert settings.POSTGRES_SERVER == "db"
        assert settings.GROQ_MODEL == "llama-3.3-70b-versatile"
        assert settings.ADMIN_API_KEY == ""  # Nueva variable para auth

    def test_config_telemetry_defaults(self):
        """Test: Configuración de telemetría tiene defaults correctos."""
        settings = Settings()

        assert settings.TWILIO_ACCOUNT_SID == ""
        assert settings.TWILIO_AUTH_TOKEN == ""
        assert settings.TELNYX_API_KEY == ""
        assert settings.TELNYX_API_BASE == "https://api.telnyx.com/v2"
