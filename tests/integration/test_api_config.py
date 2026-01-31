"""
Tests integration para endpoints de configuración (PATCH).

Valida:
- PATCH /browser - Update browser profile
- PATCH /twilio - Update Twilio profile  
- PATCH /telnyx - Update Telnyx profile
- PATCH /core - Update core config
- POST /patch - Legacy config patch
- POST /update-json - JSON config update
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app)


class TestConfigPatchEndpoints:
    """Tests para endpoints PATCH de configuración."""

    @pytest.fixture
    def mock_db_service(self):
        """Mock del db_service."""
        with patch("app.routers.config_router.db_service") as mock:
            mock.get_agent_config = AsyncMock()
            mock.save_agent_config = AsyncMock()
            yield mock

    @pytest.fixture
    def mock_config(self):
        """Mock de AgentConfig."""
        config = Mock()
        config.browser_profile = {}
        config.twilio_profile = {}
        config.telnyx_profile = {}
        config.system_prompt = "Test prompt"
        config.llm_model = "test-model"
        return config

    def test_update_browser_profile(self, mock_db_service, mock_config):
        """Verifica actualización del perfil browser."""
        mock_db_service.get_agent_config.return_value = mock_config
        
        update_data = {
            "tts_voice": "es-MX-DaliaNeural",
            "tts_rate": "10%",
            "tts_pitch": "5%"
        }
        
        response = client.patch(
            "/api/v1/config/browser",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "config" in data or "status" in data
        
        # Verificar que save fue llamado
        mock_db_service.save_agent_config.assert_called_once()

    def test_update_twilio_profile(self, mock_db_service, mock_config):
        """Verifica actualización del perfil Twilio."""
        mock_db_service.get_agent_config.return_value = mock_config
        
        update_data = {
            "tts_voice": "es-MX-DaliaNeural",
            "call_analysis_enabled": True
        }
        
        response = client.patch("/api/v1/config/twilio", json=update_data)
        
        assert response.status_code == 200
        mock_db_service.save_agent_config.assert_called_once()

    def test_update_telnyx_profile(self, mock_db_service, mock_config):
        """Verifica actualización del perfil Telnyx."""
        mock_db_service.get_agent_config.return_value = mock_config
        
        update_data = {
            "tts_voice": "es-MX-DaliaNeural",
            "background_audio_enabled": True
        }
        
        response = client.patch("/api/v1/config/telnyx", json=update_data)
        
        assert response.status_code == 200
        mock_db_service.save_agent_config.assert_called_once()

    def test_update_core_config(self, mock_db_service, mock_config):
        """Verifica actualización de configuración core."""
        mock_db_service.get_agent_config.return_value = mock_config
        
        update_data = {
            "system_prompt": "New system prompt",
            "llm_model": "llama-3.3-70b-versatile",
            "llm_temperature": 0.8
        }
        
        response = client.patch("/api/v1/config/core", json=update_data)
        
        assert response.status_code == 200
        mock_db_service.save_agent_config.assert_called_once()

    def test_update_profile_partial_data(self, mock_db_service, mock_config):
        """Verifica que actualizaciones parciales funcionan."""
        mock_db_service.get_agent_config.return_value = mock_config
        
        # Solo actualizar un campo
        update_data = {"tts_voice": "es-MX-DaliaNeural"}
        
        response = client.patch("/api/v1/config/browser", json=update_data)
        
        assert response.status_code == 200

    def test_update_profile_empty_data(self, mock_db_service, mock_config):
        """Verifica manejo de datos vacíos."""
        mock_db_service.get_agent_config.return_value = mock_config
        
        response = client.patch("/api/v1/config/browser", json={})
        
        # Puede aceptar vacío (no-op) o rechazar
        assert response.status_code in [200, 400]

    def test_update_profile_invalid_field(self, mock_db_service, mock_config):
        """Verifica manejo de campos inválidos."""
        mock_db_service.get_agent_config.return_value = mock_config
        
        update_data = {
            "invalid_field": "value",
            "another_invalid": 123
        }
        
        response = client.patch("/api/v1/config/browser", json=update_data)
        
        # Puede ignorar campos inválidos o rechazar
        assert response.status_code in [200, 422]

    def test_update_profile_db_error(self, mock_db_service, mock_config):
        """Verifica manejo de errores de DB."""
        mock_db_service.get_agent_config.return_value = mock_config
        mock_db_service.save_agent_config.side_effect = Exception("DB error")
        
        response = client.patch("/api/v1/config/browser", json={"tts_voice": "test"})
        
        assert response.status_code == 500


class TestLegacyConfigEndpoints:
    """Tests para endpoints legacy de configuración."""

    @pytest.fixture
    def mock_db_service(self):
        with patch("app.routers.config_router.db_service") as mock:
            mock.get_agent_config = AsyncMock()
            mock.save_agent_config = AsyncMock()
            yield mock

    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.to_dict = Mock(return_value={
            "llm_model": "test",
            "system_prompt": "test"
        })
        return config

    def test_legacy_patch_endpoint(self, mock_db_service, mock_config):
        """Verifica endpoint POST /patch (legacy)."""
        mock_db_service.get_agent_config.return_value = mock_config
        
        patch_data = {
            "llm_model": "new-model",
            "llm_temperature": 0.9
        }
        
        response = client.post("/api/v1/config/patch", json=patch_data)
        
        assert response.status_code == 200

    def test_legacy_update_json_endpoint(self, mock_db_service, mock_config):
        """Verifica endpoint POST /update-json (legacy)."""
        mock_db_service.get_agent_config.return_value = mock_config
        
        json_config = {
            "llm": {
                "model": "new-model",
                "temperature": 0.9
            },
            "tts": {
                "voice": "es-MX-DaliaNeural"
            }
        }
        
        response = client.post("/api/v1/config/update-json", json=json_config)
        
        assert response.status_code == 200


class TestDashboardConfigAPI:
    """Tests para endpoint de config en dashboard."""

    @pytest.fixture
    def api_headers(self):
        return {"X-API-Key": settings.API_KEY}

    @pytest.fixture
    def mock_db_service(self):
        with patch("app.routers.dashboard.db_service") as mock:
            mock.get_agent_config = AsyncMock()
            mock.save_agent_config = AsyncMock()
            yield mock

    def test_dashboard_update_config_json(self, api_headers, mock_db_service):
        """Verifica POST /api/config/update-json del dashboard."""
        mock_config = Mock()
        mock_config.to_dict = Mock(return_value={})
        mock_db_service.get_agent_config.return_value = mock_config
        
        config_data = {
            "system_prompt": "Updated prompt",
            "llm_model": "new-model"
        }
        
        response = client.post(
            "/api/config/update-json",
            json=config_data,
            headers=api_headers
        )
        
        assert response.status_code == 200

    def test_dashboard_update_config_requires_auth(self, mock_db_service):
        """Verifica que requiere autenticación."""
        response = client.post(
            "/api/config/update-json",
            json={"test": "data"}
        )
        
        assert response.status_code in [401, 403]
