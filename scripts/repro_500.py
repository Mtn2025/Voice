import asyncio
import os
import sys
from unittest.mock import AsyncMock

sys.path.append(os.getcwd())

# Bypass env
os.environ["POSTGRES_USER"] = "postgres_sim"
os.environ["POSTGRES_PASSWORD"] = "secure"
os.environ["ADMIN_API_KEY"] = "123"
os.environ["APP_ENV"] = "dev"
os.environ["SESSION_SECRET_KEY"] = "sec"

from app.db.models import AgentConfig
from app.schemas.config_schemas import BrowserConfigUpdate
from app.utils.config_utils import update_profile_config


async def repro():
    print("🚀 Reproducing Config Update Logic")

    # Mock DB Session
    mock_db = AsyncMock()

    # Mock Config Object (Simulate DB Row)
    mock_config = AgentConfig()
    mock_config.llm_model = "llama-3.3"
    mock_config.temperature = 0.5

    # Simulate get_agent_config return
    # We must patch app.services.db_service because config_utils imports it!
    # Or strict mock?

    # The utils module imports: `from app.services.db_service import db_service`
    # We need to patch that INSTANCE.

    from app.services.db_service import db_service
    db_service.get_agent_config = AsyncMock(return_value=mock_config)
    db_service.update_agent_config = AsyncMock(return_value=None)

    # Payload similar to what frontend might send (camelCase mixed?)
    # Frontend logic: `this.configs[profile]`.
    # Assuming frontend sends snake_case keys because `dashboard.php` initialized them that way.

    data = {
        "llm_model": "llama-3.3-70b-versatile",
        "temperature": 0.7,
        "system_prompt": "Test Prompt",
        # Extra key that might cause issues?
        "environment": "development", # In Global Keys
        "ignored_key": "something"
    }

    # Run Pydantic Parsing (Router does this)
    try:
        pydantic_obj = BrowserConfigUpdate(**data)
        cleaned_data = pydantic_obj.model_dump(exclude_unset=True)
        print(f"📦 Pydantic Dump: {cleaned_data.keys()}")
    except Exception as e:
        print(f"❌ Pydantic Error: {e}")
        return

    # Run Update Logic
    res = await update_profile_config(mock_db, "browser", cleaned_data)

    if res:
        print(f"✅ Result keys: {res.keys()}")
    else:
        print("❌ Result is None/Empty!")

if __name__ == "__main__":
    asyncio.run(repro())
