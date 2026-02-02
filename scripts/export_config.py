import asyncio
import json
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app.db.database import AsyncSessionLocal
from app.services.db_service import get_agent_config

async def export_config():
    async with AsyncSessionLocal() as session:
        try:
            config = await get_agent_config(session)
            # Serialize to dict (assuming Pydantic or ORM model offers .dict() or similar)
            # Since get_agent_config returns a DB model, we use simple dict serialization
            data = {
                "configs": config.configs
            }
            print(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Error exporting config: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(export_config())
