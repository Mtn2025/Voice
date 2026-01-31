
import asyncio
import os
import sys

# Fix path
sys.path.append(os.getcwd())



# Do not override Env Vars here.
# Let app.core.config load them from .env or System Env (Coolify)

from sqlalchemy import text

from app.db.database import AsyncSessionLocal


async def patch():
    # Debug: Print DB Host
    from app.core.config import settings
    db_url = settings.DATABASE_URL
    safe_url = db_url.split("@")[-1] if "@" in db_url else "UNKNOWN"
    print(f"🔌 [PATCH] Connecting to DB at {safe_url}")

    async with AsyncSessionLocal() as session:
        print("Patched DB: Adding baserow columns...")
        columns = [
            ("crm_enabled", "BOOLEAN DEFAULT FALSE"),
            ("baserow_token", "VARCHAR"),
            ("baserow_table_id", "INTEGER")
        ]

        for col_name, col_def in columns:
            try:
                await session.execute(text(f"ALTER TABLE agent_configs ADD COLUMN {col_name} {col_def}"))
                print(f"✅ Added {col_name}")
            except Exception as e:
                if "already exists" in str(e) or "duplicate column" in str(e).lower(): # Added "duplicate column" for broader compatibility
                     print(f"⚠️ {col_name} might already exist or error: {e}")
                else:
                     print(f"❌ Critical Error adding {col_name}: {e}")
                     raise e

        await session.commit()

    print("🔍 Verifying Schema...")
    async with AsyncSessionLocal() as session:
         try:
             await session.execute(text("SELECT crm_enabled FROM agent_configs LIMIT 1"))
             print("✅ Verification Passed: crm_enabled exists.")
         except Exception as e:
             print(f"❌ Verification FAILED: {e}")
             sys.exit(1)

    print("✅ DB Patch Complete.")

if __name__ == "__main__":
    try:
        asyncio.run(patch())
    except Exception as e:
        print(f"❌ Script Crashed: {e}")
        sys.exit(1)
