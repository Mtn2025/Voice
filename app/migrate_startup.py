
import logging

from sqlalchemy import text

from app.db.database import AsyncSessionLocal


async def run_migrations():
    logging.info("🔄 Checking for DB Migrations...")
    async with AsyncSessionLocal() as session:
        try:
            # 1. Add initial_silence_timeout_ms
            logging.info("Checking 'initial_silence_timeout_ms' column...")
            await session.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS initial_silence_timeout_ms INTEGER DEFAULT 5000"))

            await session.commit()
            logging.info("✅ Migrations completed successfully.")
        except Exception as e:
            logging.warning(f"⚠️ Migration warning (might be routine): {e}")
