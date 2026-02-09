
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def force_fix():
    print(f"🔌 Connecting to: {settings.DATABASE_URL.replace(settings.POSTGRES_PASSWORD, '***')}")
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        print("🔨 Dropping environment_telnyx...")
        await conn.execute(text("ALTER TABLE agent_configs DROP COLUMN IF EXISTS environment_telnyx"))
        print("🔨 Adding environment_telnyx...")
        await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN environment_telnyx VARCHAR"))
        print("✅ Done!")

    await engine.dispose()

if __name__ == "__main__":
    import os
    # Force 127.0.0.1 just in case
    # os.environ["POSTGRES_SERVER"] = "127.0.0.1" 
    # Actually let's trust the .env or override passed to it.
    asyncio.run(force_fix())
