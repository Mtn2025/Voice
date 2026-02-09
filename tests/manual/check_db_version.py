
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

# Use localhost since I exposed ports
DB_URL = "postgresql+asyncpg://postgres:CHANGE_THIS_TO_STRONG_RANDOM_PASSWORD_MIN_12_CHARS@localhost:5432/voice_db"

async def check_version():
    print(f"🔌 Connecting to {DB_URL}...")
    engine = create_async_engine(DB_URL)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        rows = result.fetchall()
        print("📊 Current DB Revisions:")
        for row in rows:
            print(f" - {row[0]}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_version())
