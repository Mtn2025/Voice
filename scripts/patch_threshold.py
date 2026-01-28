
import asyncio
import sys
import os

# Fix path
sys.path.append(os.getcwd())

from sqlalchemy import text
from app.db.database import AsyncSessionLocal

async def patch():
    print("🔌 [PATCH] Connecting to DB...")
    async with AsyncSessionLocal() as session:
        print("Patched DB: Setting input_min_characters to 2 where it is > 3...")
        # Update logic: Only fix if it's unreasonably high (like the default 10)
        await session.execute(text("UPDATE agent_configs SET input_min_characters = 2 WHERE input_min_characters > 3"))
        await session.commit()
    
    print("✅ DB Patch Complete.")

if __name__ == "__main__":
    try:
        asyncio.run(patch())
    except Exception as e:
        print(f"❌ Script Crashed: {e}")
        sys.exit(1)
