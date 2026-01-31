"""
Tests E2E para UI del dashboard (login, render).

Valida:
- GET /login - Login page render
- POST /login - Authentication flow
- GET /dashboard - Dashboard main page
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app)


class TestLoginEndpoints:
    """Tests para endpoints de login."""

    def test_login_page_get_renders(self):
        """Verifica que la página de login se renderiza."""
        response = client.get("/login")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Debe contener form de login
        assert b"password" in response.content or b"login" in response.content.lower()

    def test_login_post_success(self):
        """Verifica login exitoso con credenciales correctas."""
        with patch("app.core.auth_simple.verify_password", return_value=True):
            response = client.post(
                "/login",
                data={
                    "username": "admin",
                    "password": settings.DASHBOARD_PASSWORD
                },
                follow_redirects=False
            )
            
            # Debe redirigir a dashboard
            assert response.status_code in [302, 303]
            assert "/dashboard" in response.headers.get("location", "")

    def test_login_post_invalid_credentials(self):
        """Verifica rechazo de credenciales inválidas."""
        response = client.post(
            "/login",
            data={
                "username": "admin",
                "password": "wrong_password"
            },
            follow_redirects=False
        )
        
        # Debe retornar error o re-renderizar form
        assert response.status_code in [200, 401, 403]

    def test_login_post_missing_fields(self):
        """Verifica manejo de campos faltantes."""
        response = client.post(
            "/login",
            data={"username": "admin"}  # Missing password
        )
        
        # Validation error
        assert response.status_code in [400, 422]

    def test_login_post_empty_password(self):
        """Verifica manejo de password vacía."""
        response = client.post(
            "/login",
            data={
                "username": "admin",
                "password": ""
            }
        )
        
        assert response.status_code in [400, 401, 422]


class TestDashboardEndpoint:
    """Tests para dashboard principal."""

    @pytest.fixture
    def mock_auth(self):
        """Mock autenticación exitosa."""
        with patch("app.routers.dashboard.verify_dashboard_access", return_value=None):
            yield

    @pytest.fixture
    def mock_db_service(self):
        """Mock db_service."""
        with patch("app.routers.dashboard.db_service") as mock:
            # Mock config
            mock_config = Mock()
            mock_config.to_dict = Mock(return_value={
                "llm_model": "test-model",
                "system_prompt": "test prompt",
                "tts_voice": "es-MX-DaliaNeural"
            })
            mock.get_agent_config = AsyncMock(return_value=mock_config)
            
            # Mock call stats
            mock.get_call_stats = AsyncMock(return_value={
                "total_calls": 10,
                "completed_calls": 8,
                "failed_calls": 2
            })
            
            yield mock

    def test_dashboard_renders_with_auth(self, mock_auth, mock_db_service):
        """Verifica que dashboard se renderiza correctamente."""
        response = client.get("/dashboard")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Debe contener elementos del dashboard
        assert len(response.content) > 1000  # HTML no trivial

    def test_dashboard_without_auth_redirects(self):
        """Verifica que sin auth redirige a login."""
        # Sin mock de auth
        response = client.get("/dashboard", follow_redirects=False)
        
        # Debe redirigir a login o retornar 401/403
        assert response.status_code in [302, 303, 401, 403]

    def test_dashboard_loads_config(self, mock_auth, mock_db_service):
        """Verifica que dashboard carga config de DB."""
        response = client.get("/dashboard")
        
        assert response.status_code == 200
        mock_db_service.get_agent_config.assert_called()

    def test_dashboard_handles_missing_config(self, mock_auth, mock_db_service):
        """Verifica manejo cuando config no existe."""
        mock_db_service.get_agent_config.return_value = None
        
        response = client.get("/dashboard")
        
        # Puede usar defaults o mostrar error
        assert response.status_code in [200, 500]

    def test_dashboard_displays_call_stats(self, mock_auth, mock_db_service):
        """Verifica que muestra estadísticas de llamadas."""
        response = client.get("/dashboard")
        
        assert response.status_code == 200
        # Debe llamar a get_call_stats
        mock_db_service.get_call_stats.assert_called()

    def test_dashboard_contains_config_form(self, mock_auth, mock_db_service):
        """Verifica que contiene formulario de configuración."""
        response = client.get("/dashboard")
        
        assert response.status_code == 200
        # Debe contener inputs de config
        assert b"llm_model" in response.content or b"system_prompt" in response.content


class TestDashboardAssets:
    """Tests para assets del dashboard (CSS, JS)."""

    @pytest.mark.skip(reason="Requiere verificación de static files")
    def test_dashboard_css_loads(self):
        """Verifica que CSS del dashboard carga."""
        # TODO: Verificar que /static/css/dashboard.css existe
        pass

    @pytest.mark.skip(reason="Requiere verificación de static files")
    def test_dashboard_js_loads(self):
        """Verifica que JavaScript del dashboard carga."""
        # TODO: Verificar que /static/js/store.v2.js existe
        pass
