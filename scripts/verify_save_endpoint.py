import os
import sys
from unittest.mock import AsyncMock, patch

# Ensure app is in path
sys.path.append(os.getcwd())

# Bypass Secure Settings Validation for Simulation
os.environ["POSTGRES_USER"] = "postgres_sim_user"
os.environ["POSTGRES_PASSWORD"] = "secure_sim_password_123"
os.environ["ADMIN_API_KEY"] = "sim_api_key_12345"
os.environ["SESSION_SECRET_KEY"] = "sim_session_key_123456789"
os.environ["APP_ENV"] = "development"

from fastapi.testclient import TestClient

from app.core.auth_simple import verify_api_key
from app.db.database import get_db
from app.main import app


def test_save_simulation():
    print("🚀 Starting Simulation: Save Configuration Endpoint")

    # Override Dependencies
    app.dependency_overrides[verify_api_key] = lambda: True
    app.dependency_overrides[get_db] = lambda: AsyncMock() # Return a mock session

    client = TestClient(app)

    # Payload for Browser Config
    payload = {
        "llm_model": "llama-3.3-70b-versatile",
        "temperature": 0.7,
        "system_prompt": "You are a helpful assistant."
    }

    # Endpoint to test
    url = "/api/config/browser"

    print(f"📡 Sending PATCH request to {url}...")

    # We catch exceptions to print full traceback if app crashes
    try:
        # DB Service Mocking: We must ensure db_service.update_agent_config doesn't crash
        # Since we pass a Mock DB, `execute` will return a Mock.
        # But `db_service` might await it. `await Mock()` -> returns `mock.return_value`.
        # We need to ensure `db_service.get_agent_config` returns a Mock object with attributes.

        # ACTUALLY, simpler: Patch `app.services.db_service.db_service` entirely.
        with patch("app.services.db_service.db_service.update_agent_config", new_callable=AsyncMock) as mock_update, \
             patch("app.services.db_service.db_service.get_agent_config", new_callable=AsyncMock) as mock_get:

            mock_get.return_value = AsyncMock() # Return a mock config object
            mock_update.return_value = None

            response = client.patch(url, json=payload)

            print(f"📥 Status Code: {response.status_code}")
            print(f"📄 Response: {response.json()}")

            if response.status_code == 200:
                print("✅ Success! Config saved (Simulated).")
            else:
                print("❌ Failure!")
                sys.exit(1)

    except Exception as e:
        print(f"💥 Exception during simulation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_save_simulation()
