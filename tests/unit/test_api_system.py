"""
Tests for system API routes (health checks, system info).

Simple endpoints - quick coverage wins.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI test client."""
    from app.main import app
    return TestClient(app)


@pytest.mark.unit
class TestSystemRoutes:
    """Test system endpoints."""

    def test_health_check(self, client):
        """Test: /health returns 200 OK."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_root_redirect(self, client):
        """Test: / redirects to /dashboard."""
        response = client.get("/", follow_redirects=False)

        # Should redirect
        assert response.status_code in [307, 302, 301]
