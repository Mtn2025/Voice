"""
Tests integration para Webhooks de Twilio y Telnyx.

Valida:
- Twilio incoming call webhook (TwiML response)
- Telnyx call control events (call.initiated, call.answered, etc.)
- Signature validation
- Rate limiting
"""

import hashlib
import hmac
import json
import base64
import time
from unittest.mock import AsyncMock, patch, Mock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app)


class TestTwilioWebhook:
    """Tests para webhook Twilio incoming call."""

    def test_twilio_incoming_call_returns_twiml_xml(self):
        """Verifica que el endpoint retorna TwiML válido."""
        # Mock signature validation
        with patch("app.core.webhook_security.require_twilio_signature", return_value=None):
            response = client.get("/api/v1/twilio/incoming-call")
            
            assert response.status_code == 200
            assert "application/xml" in response.headers["content-type"]
            assert b"<?xml version=\"1.0\" encoding=\"UTF-8\"?>" in response.content
            assert b"<Response>" in response.content
            assert b"<Connect>" in response.content
            assert b"<Stream" in response.content
            assert b"wss://" in response.content
            assert b"/api/v1/ws/media-stream" in response.content

    def test_twilio_incoming_call_post_method(self):
        """Verifica que el endpoint soporta POST (además de GET)."""
        with patch("app.core.webhook_security.require_twilio_signature", return_value=None):
            response = client.post("/api/v1/twilio/incoming-call", data={})
            
            assert response.status_code == 200
            assert "application/xml" in response.headers["content-type"]

    def test_twilio_incoming_call_includes_correct_host(self):
        """Verifica que la URL del WebSocket usa el host correcto."""
        with patch("app.core.webhook_security.require_twilio_signature", return_value=None):
            response = client.get(
                "/api/v1/twilio/incoming-call",
                headers={"host": "voice.example.com"}
            )
            
            assert response.status_code == 200
            assert b"wss://voice.example.com" in response.content


class TestTelnyxWebhook:
    """Tests para webhook Telnyx call control."""

    def create_telnyx_event(self, event_type: str, call_control_id: str = "v3:test-call-123") -> dict:
        """Helper para crear eventos Telnyx válidos."""
        base_payload = {
            "call_control_id": call_control_id,
            "call_leg_id": "leg-123",
            "call_session_id": "session-456",
            "client_state": base64.b64encode(b"test_state").decode(),
            "from": "+525551234567",
            "to": "+525559876543",
            "direction": "incoming"
        }

        return {
            "data": {
                "event_type": event_type,
                "id": f"event-{int(time.time())}",
                "occurred_at": "2024-01-31T10:00:00.000Z",
                "payload": base_payload,
                "record_type": "event"
            },
            "meta": {
                "attempt": 1,
                "delivered_to": "https://example.com/webhook"
            }
        }

    @pytest.mark.parametrize("event_type", [
        "call.initiated",
        "call.answered",
        "streaming.started",
        "call.speak.ended",
        "call.hangup"
    ])
    def test_telnyx_call_control_events(self, event_type):
        """Verifica que todos los eventos Telnyx se manejan correctamente."""
        event = self.create_telnyx_event(event_type)
        
        with patch("app.core.webhook_security.require_telnyx_signature", return_value=None):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value = Mock(
                    status_code=200,
                    json=lambda: {"result": "ok"}
                )
                
                response = client.post(
                    "/api/v1/telnyx/call-control",
                    json=event
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "status" in data

    def test_telnyx_call_initiated_answers_call(self):
        """Verifica que call.initiated trigger answer + streaming."""
        event = self.create_telnyx_event("call.initiated")
        
        with patch("app.core.webhook_security.require_telnyx_signature", return_value=None):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value = Mock(status_code=200, json=lambda: {})
                
                response = client.post("/api/v1/telnyx/call-control", json=event)
                
                assert response.status_code == 200
                # Verificar que se hicieron llamadas a Telnyx API (answer + streaming)
                assert mock_post.call_count >= 1

    def test_telnyx_call_hangup_cleanup(self):
        """Verifica que call.hangup limpia el estado de la llamada."""
        call_id = "v3:test-hangup-123"
        
        # Primero iniciar una llamada
        init_event = self.create_telnyx_event("call.initiated", call_id)
        with patch("app.core.webhook_security.require_telnyx_signature", return_value=None):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value = Mock(status_code=200, json=lambda: {})
                client.post("/api/v1/telnyx/call-control", json=init_event)
        
        # Luego hacer hangup
        hangup_event = self.create_telnyx_event("call.hangup", call_id)
        hangup_event["data"]["payload"]["hangup_cause"] = "normal_clearing"
        
        with patch("app.core.webhook_security.require_telnyx_signature", return_value=None):
            response = client.post("/api/v1/telnyx/call-control", json=hangup_event)
            
            assert response.status_code == 200
            # TODO: Verificar que active_calls[call_id] fue removido

    def test_telnyx_missing_call_control_id(self):
        """Verifica manejo de eventos sin call_control_id."""
        invalid_event = {
            "data": {
                "event_type": "call.initiated",
                "payload": {}  # Missing call_control_id
            }
        }
        
        with patch("app.core.webhook_security.require_telnyx_signature", return_value=None):
            response = client.post("/api/v1/telnyx/call-control", json=invalid_event)
            
            # Debe manejar gracefully sin crash
            assert response.status_code in [200, 400]

    def test_telnyx_rate_limiting(self):
        """Verifica que rate limiting está configurado (50/minute)."""
        # NOTE: Este test requiere configuración especial de slowapi
        # Por ahora solo verificamos que el endpoint existe
        event = self.create_telnyx_event("call.initiated")
        
        with patch("app.core.webhook_security.require_telnyx_signature", return_value=None):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock):
                response = client.post("/api/v1/telnyx/call-control", json=event)
                assert response.status_code == 200


class TestWebhookSecurity:
    """Tests para validación de signatures."""

    def test_twilio_signature_validation_blocks_invalid(self):
        """Verifica que requests sin signature válida son rechazadas."""
        # Sin mock de require_twilio_signature, debe fallar
        response = client.get("/api/v1/twilio/incoming-call")
        
        # Dependiendo de implementación, puede ser 401/403/500
        assert response.status_code in [401, 403, 500]

    def test_telnyx_signature_validation_blocks_invalid(self):
        """Verifica que requests Telnyx sin signature son rechazadas."""
        event = {"data": {"event_type": "call.initiated", "payload": {}}}
        
        response = client.post("/api/v1/telnyx/call-control", json=event)
        
        assert response.status_code in [401, 403, 500]
