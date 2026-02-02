import asyncio
import json
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app.db.database import AsyncSessionLocal
from app.db.models import AgentConfig
from sqlalchemy import select

async def import_config():
    # Read JSON from stdin
    try:
        input_data = sys.stdin.read()
        if not input_data:
            print("No input data provided", file=sys.stderr)
            sys.exit(1)
            
        data = json.loads(input_data)
        configs = data.get("configs", {})
        
        async with AsyncSessionLocal() as session:
            # Upsert logic: get existing config or create new
            result = await session.execute(select(AgentConfig).limit(1))
            agent_config = result.scalars().first()
            
            if not agent_config:
                agent_config = AgentConfig(configs={})
                session.add(agent_config)
            
            # Merge/Overwrite configs
            agent_config.configs = configs
            await session.commit()
            print("Successfully imported configuration.")
            
    except Exception as e:
        print(f"Error importing config: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(import_config())
