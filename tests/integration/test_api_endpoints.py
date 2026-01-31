"""
Tests integration para endpoints API (context injection, voice preview, outbound).

Valida:
- POST /api/v1/calls/{call_id}/context - Dynamic context injection
- POST /api/voice/preview - Voice synthesis preview
- POST /api/v1/calls/test-outbound - Test outbound calls
"""

import base64
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app)


class TestContextInjectionAPI:
    """Tests para endpoint de inyección dinámica de contexto."""

    @pytest.fixture
    def mock_manager(self):
        """Mock del ConnectionManager."""
        with patch("app.api.routes_v2.manager") as mock:
            mock.active_connections = {}
            yield mock

    @pytest.fixture
    def api_headers(self):
        """Headers con API key para autenticación."""
        return {"X-API-Key": settings.API_KEY}

    def test_context_injection_success(self, mock_manager, api_headers):
        """Verifica inyección exitosa de contexto en llamada activa."""
        call_id = "test-call-123"
        
        # Simular conexión activa
        mock_orchestrator = Mock()
        mock_orchestrator.control_channel = Mock()
        mock_orchestrator.control_channel.inject_context = Mock()
        mock_manager.active_connections = {call_id: mock_orchestrator}
        
        context_data = {
            "customer_name": "Juan Pérez",
            "account_type": "VIP",
            "balance": 15000.50
        }
        
        response = client.post(
            f"/api/v1/calls/{call_id}/context",
            json=context_data,
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "context_injected"
        assert data["call_id"] == call_id

    def test_context_injection_call_not_found(self, mock_manager, api_headers):
        """Verifica error 404 cuando el call_id no existe."""
        mock_manager.active_connections = {}
        
        response = client.post(
            "/api/v1/calls/nonexistent-call/context",
            json={"context": "test"},
            headers=api_headers
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_context_injection_requires_auth(self, mock_manager):
        """Verifica que el endpoint requiere API key."""
        response = client.post(
            "/api/v1/calls/test-123/context",
            json={"context": "test"}
            # Sin headers de auth
        )
        
        assert response.status_code in [401, 403]

    def test_context_injection_empty_context(self, mock_manager, api_headers):
        """Verifica manejo de contexto vacío."""
        call_id = "test-call-123"
        mock_orchestrator = Mock()
        mock_manager.active_connections = {call_id: mock_orchestrator}
        
        response = client.post(
            f"/api/v1/calls/{call_id}/context",
            json={},  # Contexto vacío
            headers=api_headers
        )
        
        # Debe aceptar contexto vacío (puede ser usado para clear context)
        assert response.status_code in [200, 400]

    def test_context_injection_large_context(self, mock_manager, api_headers):
        """Verifica manejo de contexto grande."""
        call_id = "test-call-123"
        mock_orchestrator = Mock()
        mock_manager.active_connections = {call_id: mock_orchestrator}
        
        # Contexto con muchos campos
        large_context = {f"field_{i}": f"value_{i}" for i in range(100)}
        
        response = client.post(
            f"/api/v1/calls/{call_id}/context",
            json=large_context,
            headers=api_headers
        )
        
        assert response.status_code == 200


class TestVoicePreviewAPI:
    """Tests para endpoint de preview de voz (TTS synthesis)."""

    @pytest.fixture
    def api_headers(self):
        """Headers con API key."""
        return {"X-API-Key": settings.API_KEY}

    def test_voice_preview_success(self, api_headers):
        """Verifica síntesis exitosa de audio preview."""
        with patch("app.routers.dashboard.db_service") as mock_db:
            # Mock config
            mock_config = Mock()
            mock_config.tts_provider = "azure"
            mock_config.tts_voice = "es-MX-DaliaNeural"
            mock_config.tts_rate = "0%"
            mock_db.get_agent_config = AsyncMock(return_value=mock_config)
            
            # Mock TTS adapter
            with patch("app.adapters.outbound.tts.azure_tts_adapter.AzureTTSAdapter") as mock_tts:
                mock_instance = AsyncMock()
                mock_instance.synthesize = AsyncMock(return_value=b"fake_audio_data")
                mock_tts.return_value = mock_instance
                
                payload = {
                    "text": "Hola, esto es una prueba de voz",
                    "provider": "azure",
                    "voice": "es-MX-DaliaNeural"
                }
                
                response = client.post(
                    "/api/voice/preview",
                    json=payload,
                    headers=api_headers
                )
                
                assert response.status_code == 200
                assert response.headers["content-type"] == "audio/mpeg"
                assert len(response.content) > 0

    def test_voice_preview_requires_auth(self):
        """Verifica que requiere autenticación."""
        response = client.post(
            "/api/voice/preview",
            json={"text": "test"}
        )
        
        assert response.status_code in [401, 403]

    def test_voice_preview_empty_text(self, api_headers):
        """Verifica manejo de texto vacío."""
        response = client.post(
            "/api/voice/preview",
            json={"text": "", "provider": "azure"},
            headers=api_headers
        )
        
        # Puede ser 400 (bad request) o 200 con audio silencio
        assert response.status_code in [200, 400]

    def test_voice_preview_long_text(self, api_headers):
        """Verifica síntesis de texto largo."""
        with patch("app.routers.dashboard.db_service") as mock_db:
            mock_config = Mock()
            mock_config.tts_provider = "azure"
            mock_db.get_agent_config = AsyncMock(return_value=mock_config)
            
            with patch("app.adapters.outbound.tts.azure_tts_adapter.AzureTTSAdapter") as mock_tts:
                mock_instance = AsyncMock()
                mock_instance.synthesize = AsyncMock(return_value=b"audio" * 1000)
                mock_tts.return_value = mock_instance
                
                long_text = "Texto largo. " * 100  # ~1200 caracteres
                
                response = client.post(
                    "/api/voice/preview",
                    json={"text": long_text, "provider": "azure"},
                    headers=api_headers
                )
                
                # Debe manejar texto largo
                assert response.status_code in [200, 413]  # 413 = Payload Too Large

    def test_voice_preview_invalid_provider(self, api_headers):
        """Verifica manejo de provider inválido."""
        response = client.post(
            "/api/voice/preview",
            json={"text": "test", "provider": "invalid_provider"},
            headers=api_headers
        )
        
        assert response.status_code in [400, 500]


class TestOutboundCallAPI:
    """Tests para endpoint de test outbound call."""

    @pytest.fixture
    def api_headers(self):
        return {"X-API-Key": settings.API_KEY}

    def test_outbound_call_success(self, api_headers):
        """Verifica inicio exitoso de llamada outbound."""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            # Mock respuesta exitosa de Telnyx
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {
                    "data": {
                        "call_control_id": "v3:test-outbound-123",
                        "call_leg_id": "leg-123"
                    }
                }
            )
            
            payload = {
                "to": "+525551234567",
                "message": "Test outbound call"
            }
            
            response = client.post(
                "/api/v1/calls/test-outbound",
                json=payload,
                headers=api_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "call_control_id" in data or "status" in data

    def test_outbound_call_requires_auth(self):
        """Verifica autenticación requerida."""
        response = client.post(
            "/api/v1/calls/test-outbound",
            json={"to": "+5255512345"}
        )
        
        assert response.status_code in [401, 403]

    def test_outbound_call_invalid_number(self, api_headers):
        """Verifica manejo de número inválido."""
        response = client.post(
            "/api/v1/calls/test-outbound",
            json={"to": "invalid", "message": "test"},
            headers=api_headers
        )
        
        # Puede ser validado en el endpoint o fallar en Telnyx
        assert response.status_code in [400, 500]

    def test_outbound_call_telnyx_error(self, api_headers):
        """Verifica manejo de error de Telnyx API."""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            # Mock error de Telnyx
            mock_post.return_value = Mock(
                status_code=400,
                json=lambda: {"errors": [{"detail": "Invalid number"}]}
            )
            
            response = client.post(
                "/api/v1/calls/test-outbound",
                json={"to": "+123", "message": "test"},
                headers=api_headers
            )
            
            assert response.status_code in [400, 500]
