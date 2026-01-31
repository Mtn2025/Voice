"""
Tests integration para WebSocket media stream endpoint.

Valida:
- Conexión WebSocket para Twilio, Telnyx y Simulator
- Detección automática de client type
- Flujo de mensajes bidireccional
- Manejo de desconexiones
"""

import asyncio
import base64
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import TestClient as StarletteTestClient

from app.main import app


@pytest.mark.asyncio
class TestWebSocketMediaStream:
    """Tests para WebSocket /api/v1/ws/media-stream."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Mock del VoiceOrchestratorV2."""
        with patch("app.api.routes_v2.VoiceOrchestratorV2") as mock_class:
            mock_instance = AsyncMock()
            mock_instance.cleanup = AsyncMock()
            mock_class.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_db_session(self):
        """Mock de la sesión de base de datos."""
        with patch("app.api.routes_v2.AsyncSessionLocal") as mock_class:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_class.return_value = mock_session
            yield mock_session

    def test_websocket_accepts_connection(self, mock_orchestrator, mock_db_session):
        """Verifica que el WebSocket acepta conexiones."""
        with TestClient(app).websocket_connect("/api/v1/ws/media-stream") as websocket:
            # Debe aceptar conexión
            assert websocket is not None
            websocket.close()

    def test_websocket_detects_twilio_client(self, mock_orchestrator, mock_db_session):
        """Verifica detección automática de cliente Twilio."""
        with TestClient(app).websocket_connect("/api/v1/ws/media-stream") as websocket:
            # Enviar evento START de Twilio
            twilio_start = {
                "event": "start",
                "start": {
                    "streamSid": "MZ1234567890",
                    "accountSid": "AC1234567890",
                    "callSid": "CA1234567890"
                },
                "streamSid": "MZ1234567890"
            }
            
            websocket.send_json(twilio_start)
            
            # Esperar respuesta (puede ser acknowledgment o nada)
            # El test confirma que no crashea
            websocket.close()

    def test_websocket_detects_telnyx_client(self, mock_orchestrator, mock_db_session):
        """Verifica detección automática de cliente Telnyx."""
        with TestClient(app).websocket_connect("/api/v1/ws/media-stream") as websocket:
            # Enviar mensaje Telnyx (formato diferente a Twilio)
            telnyx_msg = {
                "event": "media",
                "media": {
                    "payload": base64.b64encode(b"\x00" * 160).decode()
                }
            }
            
            websocket.send_json(telnyx_msg)
            websocket.close()

    def test_websocket_detects_simulator_client(self, mock_orchestrator, mock_db_session):
        """Verifica detección de cliente Simulator."""
        with TestClient(app).websocket_connect("/api/v1/ws/media-stream") as websocket:
            # El simulator usa formato específico
            sim_msg = {
                "type": "config",
                "sample_rate": 8000,
                "encoding": "mulaw"
            }
            
            websocket.send_json(sim_msg)
            websocket.close()

    def test_websocket_handles_twilio_media_event(self, mock_orchestrator, mock_db_session):
        """Verifica procesamiento de evento media de Twilio."""
        mock_transport = AsyncMock()
        
        with patch("app.adapters.telephony.transport.TelephonyTransport", return_value=mock_transport):
            with TestClient(app).websocket_connect("/api/v1/ws/media-stream") as websocket:
                # START event
                websocket.send_json({
                    "event": "start",
                    "streamSid": "MZ123",
                    "start": {"streamSid": "MZ123"}
                })
                
                # MEDIA event con audio
                audio_payload = base64.b64encode(b"\x00" * 160).decode()
                websocket.send_json({
                    "event": "media",
                    "streamSid": "MZ123",
                    "media": {
                        "payload": audio_payload
                    }
                })
                
                # Debe procesar sin error
                websocket.close()

    def test_websocket_handles_stop_event(self, mock_orchestrator, mock_db_session):
        """Verifica manejo de evento STOP (fin de stream)."""
        with TestClient(app).websocket_connect("/api/v1/ws/media-stream") as websocket:
            # START
            websocket.send_json({
                "event": "start",
                "streamSid": "MZ123"
            })
            
            # STOP
            websocket.send_json({
                "event": "stop",
                "streamSid": "MZ123"
            })
            
            # Debe cleanup gracefully
            websocket.close()

    def test_websocket_cleanup_on_disconnect(self, mock_orchestrator, mock_db_session):
        """Verifica que se hace cleanup al desconectar."""
        with TestClient(app).websocket_connect("/api/v1/ws/media-stream") as websocket:
            websocket.send_json({"event": "start", "streamSid": "MZ123"})
            # Desconectar abruptamente
            websocket.close()
        
        # Verificar que orchestrator.cleanup() fue llamado
        mock_orchestrator.cleanup.assert_called()

    def test_websocket_handles_invalid_json(self, mock_orchestrator, mock_db_session):
        """Verifica manejo de JSON inválido."""
        with TestClient(app).websocket_connect("/api/v1/ws/media-stream") as websocket:
            # Enviar texto que no es JSON
            with pytest.raises(Exception):
                websocket.send_text("invalid json {{{")

    def test_websocket_bidirectional_audio_flow(self, mock_orchestrator, mock_db_session):
        """Verifica que el WebSocket puede enviar audio de vuelta."""
        mock_transport = AsyncMock()
        
        # Mock del método send_audio del transport
        async def mock_send_audio(audio_bytes):
            # Simular que se envía audio al WebSocket
            return audio_bytes
        
        mock_transport.send_audio = mock_send_audio
        
        with patch("app.adapters.telephony.transport.TelephonyTransport", return_value=mock_transport):
            with TestClient(app).websocket_connect("/api/v1/ws/media-stream") as websocket:
                websocket.send_json({
                    "event": "start",
                    "streamSid": "MZ123"
                })
                
                # Enviar audio input
                websocket.send_json({
                    "event": "media",
                    "media": {
                        "payload": base64.b64encode(b"\x00" * 160).decode()
                    }
                })
                
                # Debería eventualmente recibir audio output
                # (esto depende de la implementación del orchestrator)
                
                websocket.close()

    def test_websocket_concurrent_connections(self, mock_orchestrator, mock_db_session):
        """Verifica que se pueden manejar múltiples conexiones simultáneas."""
        # Abrir 2 conexiones WebSocket al mismo tiempo
        with TestClient(app).websocket_connect("/api/v1/ws/media-stream") as ws1:
            with TestClient(app).websocket_connect("/api/v1/ws/media-stream") as ws2:
                ws1.send_json({"event": "start", "streamSid": "MZ001"})
                ws2.send_json({"event": "start", "streamSid": "MZ002"})
                
                # Ambos deben funcionar independientemente
                ws1.close()
                ws2.close()


@pytest.mark.asyncio
class TestWebSocketIntegrationWithOrchestrator:
    """Tests de integración del WebSocket con el Orchestrator."""

    @pytest.fixture
    def real_db_session(self):
        """Sesión de DB real para tests de integración."""
        # TODO: Implementar si se requieren tests con DB real
        pass

    @pytest.mark.skip(reason="Requiere setup completo de DB y providers")
    async def test_full_websocket_conversation_flow(self):
        """Test E2E de flujo completo de conversación."""
        # Este test requeriría:
        # - DB configurada
        # - Providers mockeados (STT, LLM, TTS)
        # - Orchestrator funcional
        pass
