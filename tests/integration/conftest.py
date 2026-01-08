"""
Integration Tests - Configuration Fixtures

Shared fixtures for integration testing.
"""
import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Set required env vars if not already set
    test_env = {
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_SERVER": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "test_db",
        "ADMIN_API_KEY": "test-integration-key",
        "AZURE_SPEECH_KEY": "fake-key",
        "AZURE_SPEECH_REGION": "eastus",
        "GROQ_API_KEY": "fake-key",
        "TWILIO_AUTH_TOKEN": "fake-token",
        "REDIS_URL": "redis://localhost:6379",
    }
    
    for key, value in test_env.items():
        if key not in os.environ:
            os.environ[key] = value
    
    yield
    
    # Cleanup not needed - env vars are process-scoped


@pytest.fixture
def integration_client():
    """Provide HTTP client for integration tests."""
    from httpx import AsyncClient
    from app.main import app
    
    return AsyncClient(app=app, base_url="http://test")
