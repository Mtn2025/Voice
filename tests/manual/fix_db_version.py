
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_URL = "postgresql+asyncpg://postgres:CHANGE_THIS_TO_STRONG_RANDOM_PASSWORD_MIN_12_CHARS@localhost:5432/voice_db"

async def fix_version():
    print(f"🔌 Connecting to {DB_URL}...")
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        print("🛠️ Updating alembic_version to 'merge_heads_20260201'...")
        await conn.execute(text("UPDATE alembic_version SET version_num = 'merge_heads_20260201'"))
        print("✅ Done.")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_version())
