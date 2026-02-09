
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, inspect
import sys

# Use localhost since I exposed ports
DB_URL = "postgresql+asyncpg://postgres:CHANGE_THIS_TO_STRONG_RANDOM_PASSWORD_MIN_12_CHARS@localhost:5432/voice_db"

async def check_columns():
    print(f"🔌 Connecting to {DB_URL}...")
    engine = create_async_engine(DB_URL)
    async with engine.connect() as conn:
        print("📊 Inspecting agent_configs columns...")
        # Raw SQL to check columns
        result = await conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'agent_configs'"))
        rows = result.fetchall()
        
        found = False
        print("\n--- COLUMNS FOUND ---")
        for row in rows:
            print(f" - {row[0]} ({row[1]})")
            if row[0] == 'environment_telnyx':
                found = True
        
        print("\n---------------------")
        if found:
            print("✅ 'environment_telnyx' column EXISTS.")
        else:
            print("❌ 'environment_telnyx' column MISSING.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_columns())
