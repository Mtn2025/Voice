
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def debug_db():
    print(f"🔌 Connecting to: {settings.DATABASE_URL.replace(settings.POSTGRES_PASSWORD, '***')}")
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.connect() as conn:
        print("✅ Connected!")
        
        # Fingerprint
        version = await conn.execute(text("SELECT version()"))
        print(f"🆔 DB Version: {version.scalar()}")
        pid = await conn.execute(text("SELECT pg_backend_pid()"))
        print(f"🆔 Backend PID: {pid.scalar()}")
        addr = await conn.execute(text("SELECT inet_server_addr()"))
        print(f"🆔 Server Addr: {addr.scalar()}")

        print("📊 Checking 'privacy_mode_phone' in 'agent_configs'...")
        try:
            # Check using information_schema
            result = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'agent_configs' AND column_name = 'environment_telnyx'"))
            row = result.fetchone()
            if row:
                print(f"✅ Found column via schema: {row[0]}")
            else:
                print("❌ Column NOT FOUND via schema.")
                
            # Check using SELECT
            # Check using SELECT
            try:
                await conn.execute(text("SELECT privacy_mode_phone FROM agent_configs LIMIT 1"))
                print("✅ SELECT privacy_mode_phone succeeded.")
            except Exception as e:
                 print(f"❌ SELECT privacy_mode_phone FAILED: {e}")
                 
        except Exception as e:
            print(f"❌ Error during inspection: {e}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(debug_db())
