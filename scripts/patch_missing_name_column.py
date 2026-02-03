import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Construct from components
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_SERVER", "db") # 'db' is the docker service name
    port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "voice_db_v2")
    DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"

async def patch_db():
    print(f"🔌 Connecting to DB: {DATABASE_URL}")
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        print("🛠️ Checking agent_configs table...")
        try:
            # Check if column exists
            result = await conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='agent_configs' AND column_name='name';"
            ))
            if result.scalar():
                print("✅ Column 'name' already exists.")
            else:
                print("⚠️ Column 'name' MISSING. Adding it...")
                await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN name VARCHAR DEFAULT 'default';"))
                # Make it unique and index if needed, but lets verify functionality first
                await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_agent_configs_name ON agent_configs (name);"))
                print("✅ Column 'name' added successfully.")
        except Exception as e:
            print(f"❌ Error patching DB: {e}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(patch_db())
