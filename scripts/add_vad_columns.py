
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
    # Debug: Print DB Host (Masking password)
    from app.core.config import settings
    db_url = settings.DATABASE_URL
    safe_url = db_url.split("@")[-1] if "@" in db_url else "UNKNOWN"
    print(f"🔌 [PATCH] Connecting to DB at {safe_url}")

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
                # If column exists, it's fine. But we should differentiate.
                if "already exists" in str(e) or "UndefinedColumn" not in str(e): 
                     print(f"⚠️ {col_name} might already exist or error: {e}")
                else:
                    print(f"❌ Critical Error adding {col_name}: {e}")
                    raise e
        
        await session.commit()
    
    # Final Verification
    print("🔍 Verifying Schema...")
    async with AsyncSessionLocal() as session:
         try:
             # Check if column exists by selecting it
             await session.execute(text("SELECT vad_threshold FROM agent_configs LIMIT 1"))
             print("✅ Verification Passed: vad_threshold exists.")
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
