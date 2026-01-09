
import asyncio

from sqlalchemy import text

from app.db.database import AsyncSessionLocal


async def patch():
    async with AsyncSessionLocal() as session:
        print("Patched DB: Adding inactivity_max_retries...")
        try:
            await session.execute(text("ALTER TABLE agent_configs ADD COLUMN inactivity_max_retries INTEGER DEFAULT 3"))
            await session.commit()
            print("✅ Success!")
        except Exception as e:
            print(f"⚠️ Error (maybe already exists): {e}")

if __name__ == "__main__":
    asyncio.run(patch())
