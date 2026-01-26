
import asyncio
import sys
import os

# Fix path
sys.path.append(os.getcwd())
# Fix path
sys.path.append(os.getcwd())

# Do not override Env Vars here. 
# Let app.core.config load them from .env or System Env (Coolify)

from sqlalchemy import text
from app.db.database import AsyncSessionLocal

async def patch():
    async with AsyncSessionLocal() as session:
        print("Patched DB: Adding vad_threshold columns...")
        columns = [
            ("vad_threshold", "FLOAT DEFAULT 0.5"),
            ("vad_threshold_phone", "FLOAT DEFAULT 0.5"),
            ("vad_threshold_telnyx", "FLOAT DEFAULT 0.5")
        ]
        
        for col_name, col_def in columns:
            try:
                await session.execute(text(f"ALTER TABLE agent_configs ADD COLUMN {col_name} {col_def}"))
                print(f"✅ Added {col_name}")
            except Exception as e:
                print(f"⚠️ Error adding {col_name} (likely exists): {e}")
        
        await session.commit()
        print("✅ DB Patch Complete.")

if __name__ == "__main__":
    asyncio.run(patch())
