
import asyncio
import sys
import os

# Fix path
sys.path.append(os.getcwd())

# Bypass Pydantic validation for script
os.environ["POSTGRES_USER"] = "postgres_secure_user"
if not os.environ.get("POSTGRES_SERVER"):
    os.environ["POSTGRES_SERVER"] = "localhost"

from sqlalchemy import text
from app.db.database import AsyncSessionLocal

async def patch():
    async with AsyncSessionLocal() as session:
        print("Patched DB: Adding Webhook columns...")
        
        columns = [
            ("webhook_url", "VARCHAR"),
            ("webhook_secret", "VARCHAR")
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
