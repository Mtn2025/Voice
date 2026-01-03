
import asyncio
from app.db.database import engine, Base
from app.db.models import Call, Transcript
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_history():
    logger.info("🗑️  Clearing History (Dropping Tables)...")
    async with engine.begin() as conn:
        # We drop specific tables to avoid losing AgentConfig
        await conn.run_sync(Base.metadata.drop_all, tables=[Call.__table__, Transcript.__table__])
        logger.info("✅ Calls and Transcripts Dropped.")
        
        # Re-create all tables (this will recreate Calls and Transcripts with new Schema)
        # AgentConfig will be practically untouched if it wasn't dropped, 
        # but create_all handles checking existence.
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database Re-Created with new Schema (client_type included).")

if __name__ == "__main__":
    asyncio.run(migrate_history())
