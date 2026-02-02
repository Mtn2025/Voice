import pytest
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_redirect_deprecated_endpoint():
    """Verify /calls/test-outbound redirects to /admin/test-call-telnyx"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/calls/test-outbound", json={"to": "+1234567890"})
        # 307 redirect
        assert response.status_code == 307
        assert response.headers["location"] == "/admin/test-call-telnyx"

@pytest.mark.asyncio
async def test_admin_endpoint_structure():
    """Verify admin endpoints exist (authentication failure expected but confirms path)"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Should return 401/403 or 422 if auth is missing, but NOT 404
        response = await ac.post("/admin/test-call-telnyx", json={})
        assert response.status_code != 404
        
        response = await ac.get("/admin/config")
        assert response.status_code != 404

@pytest.mark.asyncio
async def test_telephony_routes_exist():
    """Verify telephony routes exist at /api/v1..."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Twilio
        response = await ac.post("/api/v1/twilio/incoming-call")
        assert response.status_code != 404
        
        # Telnyx
        response = await ac.post("/api/v1/telnyx/call-control")
        assert response.status_code != 404

@pytest.mark.asyncio
async def test_simulator_ws_route():
    """Verify simulator WebSocket route exists"""
    with client.websocket_connect("/ws/simulator/stream") as websocket:
        # If connection accepted or at least handshake starts (might fail auth/manager but path is valid)
        # We assume it accepts or rejects, but not 404
        pass  # Success if no 404/ConnectionRefused on path lookup
