
import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text

async def patch():
    async with AsyncSessionLocal() as session:
        print("Patched DB: Adding initial_silence_timeout_ms...")
        try:
            await session.execute(text("ALTER TABLE agent_configs ADD COLUMN initial_silence_timeout_ms INTEGER DEFAULT 5000"))
            await session.commit()
            print("✅ Success!")
        except Exception as e:
            print(f"⚠️ Error (maybe already exists): {e}")

if __name__ == "__main__":
    asyncio.run(patch())
