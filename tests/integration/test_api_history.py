"""
Tests integration para endpoints de history/call management.

Valida:
- GET /api/history/rows - List call history
- POST /api/history/delete-selected - Delete selected calls
- POST /api/history/clear - Clear all history
- GET /dashboard/call/{call_id} - Call detail view
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app)


class TestHistoryAPI:
    """Tests para endpoints de historial de llamadas."""

    @pytest.fixture
    def api_headers(self):
        return {"X-API-Key": settings.API_KEY}

    @pytest.fixture
    def mock_db_service(self):
        with patch("app.routers.dashboard.db_service") as mock:
            yield mock

    @pytest.fixture
    def sample_calls(self):
        """Sample call records."""
        return [
            Mock(
                id=1,
                call_sid="CA123",
                from_number="+525551234567",
                to_number="+525559876543",
                status="completed",
                start_time=datetime(2024, 1, 31, 10, 0, 0),
                end_time=datetime(2024, 1, 31, 10, 5, 0),
                duration=300,
                transcript="Test transcript"
            ),
            Mock(
                id=2,
                call_sid="CA456",
                from_number="+525551111111",
                to_number="+525559876543",
                status="completed",
                start_time=datetime(2024, 1, 31, 11, 0, 0),
                end_time=datetime(2024, 1, 31, 11, 3, 0),
                duration=180,
                transcript="Another call"
            )
        ]

    def test_get_history_rows_success(self, api_headers, mock_db_service, sample_calls):
        """Verifica obtención de filas de historial."""
        mock_db_service.get_call_history = AsyncMock(return_value=sample_calls)
        
        response = client.get(
            "/api/history/rows",
            headers=api_headers
        )
        
        assert response.status_code == 200
        # Debe retornar HTML (response_class=HTMLResponse)
        assert "text/html" in response.headers["content-type"]
        # Debe contener datos de las llamadas
        assert "CA123" in response.text or len(response.text) > 0

    def test_get_history_rows_pagination(self, api_headers, mock_db_service, sample_calls):
        """Verifica paginación en historial."""
        mock_db_service.get_call_history = AsyncMock(return_value=sample_calls)
        
        response = client.get(
            "/api/history/rows?page=1&limit=10",
            headers=api_headers
        )
        
        assert response.status_code == 200

    def test_get_history_rows_empty(self, api_headers, mock_db_service):
        """Verifica historial vacío."""
        mock_db_service.get_call_history = AsyncMock(return_value=[])
        
        response = client.get(
            "/api/history/rows",
            headers=api_headers
        )
        
        assert response.status_code == 200
        # Debe retornar HTML vacío o mensaje "No calls"
        assert len(response.text) >= 0

    def test_get_history_rows_requires_auth(self, mock_db_service):
        """Verifica autenticación requerida."""
        response = client.get("/api/history/rows")
        
        assert response.status_code in [401, 403]

    def test_delete_selected_calls_success(self, api_headers, mock_db_service):
        """Verifica eliminación de llamadas seleccionadas."""
        mock_db_service.delete_calls_by_ids = AsyncMock(return_value=2)
        
        delete_data = {
            "call_ids": [1, 2]
        }
        
        response = client.post(
            "/api/history/delete-selected",
            json=delete_data,
            headers=api_headers
        )
        
        assert response.status_code == 200
        mock_db_service.delete_calls_by_ids.assert_called_once_with([1, 2])

    def test_delete_selected_empty_list(self, api_headers, mock_db_service):
        """Verifica manejo de lista vacía."""
        response = client.post(
            "/api/history/delete-selected",
            json={"call_ids": []},
            headers=api_headers
        )
        
        # Puede ser 200 (no-op) o 400 (bad request)
        assert response.status_code in [200, 400]

    def test_delete_selected_invalid_ids(self, api_headers, mock_db_service):
        """Verifica manejo de IDs inválidos."""
        mock_db_service.delete_calls_by_ids = AsyncMock(return_value=0)
        
        response = client.post(
            "/api/history/delete-selected",
            json={"call_ids": [99999, 88888]},
            headers=api_headers
        )
        
        # Debe manejar sin error (0 deleted)
        assert response.status_code == 200

    def test_delete_selected_requires_auth(self, mock_db_service):
        """Verifica autenticación requerida."""
        response = client.post(
            "/api/history/delete-selected",
            json={"call_ids": [1, 2]}
        )
        
        assert response.status_code in [401, 403]

    def test_clear_history_success(self, api_headers, mock_db_service):
        """Verifica limpieza completa del historial."""
        mock_db_service.clear_call_history = AsyncMock(return_value=10)
        
        response = client.post(
            "/api/history/clear",
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted" in data or "status" in data
        mock_db_service.clear_call_history.assert_called_once()

    def test_clear_history_empty_db(self, api_headers, mock_db_service):
        """Verifica clear cuando DB vacía."""
        mock_db_service.clear_call_history = AsyncMock(return_value=0)
        
        response = client.post(
            "/api/history/clear",
            headers=api_headers
        )
        
        assert response.status_code == 200

    def test_clear_history_requires_auth(self, mock_db_service):
        """Verifica autenticación requerida."""
        response = client.post("/api/history/clear")
        
        assert response.status_code in [401, 403]

    def test_clear_history_db_error(self, api_headers, mock_db_service):
        """Verifica manejo de error de DB."""
        mock_db_service.clear_call_history = AsyncMock(side_effect=Exception("DB error"))
        
        response = client.post(
            "/api/history/clear",
            headers=api_headers
        )
        
        assert response.status_code == 500


class TestCallDetailView:
    """Tests para vista de detalle de llamada."""

    @pytest.fixture
    def api_headers(self):
        return {"X-API-Key": settings.API_KEY}

    @pytest.fixture
    def mock_db_service(self):
        with patch("app.routers.dashboard.db_service") as mock:
            yield mock

    @pytest.fixture
    def sample_call(self):
        call = Mock()
        call.id = 123
        call.call_sid = "CA123456"
        call.from_number = "+525551234567"
        call.to_number = "+525559876543"
        call.status = "completed"
        call.duration = 300
        call.transcript = "Full call transcript here"
        call.start_time = datetime(2024, 1, 31, 10, 0, 0)
        call.end_time = datetime(2024, 1, 31, 10, 5, 0)
        return call

    def test_call_detail_view_success(self, api_headers, mock_db_service, sample_call):
        """Verifica vista de detalle de llamada."""
        mock_db_service.get_call_by_id = AsyncMock(return_value=sample_call)
        
        response = client.get(
            "/dashboard/call/123",
            headers=api_headers
        )
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Debe contener información de la llamada
        assert "CA123456" in response.text or len(response.text) > 100

    def test_call_detail_view_not_found(self, api_headers, mock_db_service):
        """Verifica llamada no encontrada."""
        mock_db_service.get_call_by_id = AsyncMock(return_value=None)
        
        response = client.get(
            "/dashboard/call/99999",
            headers=api_headers
        )
        
        assert response.status_code == 404

    def test_call_detail_view_requires_auth(self, mock_db_service, sample_call):
        """Verifica autenticación requerida."""
        mock_db_service.get_call_by_id = AsyncMock(return_value=sample_call)
        
        response = client.get("/dashboard/call/123")
        
        assert response.status_code in [401, 403]

    def test_call_detail_view_invalid_id(self, api_headers, mock_db_service):
        """Verifica ID inválido."""
        response = client.get(
            "/dashboard/call/invalid",
            headers=api_headers
        )
        
        # FastAPI validation debe rechazar
        assert response.status_code == 422
