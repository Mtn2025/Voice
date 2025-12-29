
import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text
import logging

# Configure minimal logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

async def run_migration():
    async with AsyncSessionLocal() as session:
        logger.info("🚀 Starting database migration for Phone Config columns...")
        
        # List of columns to add with their types and defaults
        # Format: (column_name, sql_type_def)
        columns_to_add = [
            ("stt_language", "VARCHAR DEFAULT 'es-MX'"),
            ("interruption_threshold_phone", "INTEGER DEFAULT 2"),
            ("voice_style", "VARCHAR"),
            ("voice_speed_phone", "FLOAT DEFAULT 0.9"),
            
            # Phone Profile Keys
            ("stt_provider_phone", "VARCHAR DEFAULT 'azure'"),
            ("stt_language_phone", "VARCHAR DEFAULT 'es-MX'"),
            ("llm_provider_phone", "VARCHAR DEFAULT 'groq'"),
            ("llm_model_phone", "VARCHAR DEFAULT 'llama-3.3-70b-versatile'"),
            ("system_prompt_phone", "TEXT"),
            
            ("voice_name_phone", "VARCHAR DEFAULT 'es-MX-DaliaNeural'"),
            ("voice_style_phone", "VARCHAR"),
            ("temperature_phone", "FLOAT DEFAULT 0.7"),
            
            ("first_message_phone", "VARCHAR DEFAULT 'Hola, soy Andrea de Ubrokers. ¿Me escucha bien?'"),
            ("first_message_mode_phone", "VARCHAR DEFAULT 'speak-first'"),
            ("max_tokens_phone", "INTEGER DEFAULT 250"),
            
            ("initial_silence_timeout_ms_phone", "INTEGER DEFAULT 5000"),
            ("input_min_characters_phone", "INTEGER DEFAULT 1"),
            ("enable_denoising_phone", "BOOLEAN DEFAULT TRUE"),
            ("silence_timeout_ms_phone", "INTEGER DEFAULT 1200"),
            
            # Twilio Specifics
            ("twilio_machine_detection", "VARCHAR DEFAULT 'Enable'"),
            ("twilio_record", "BOOLEAN DEFAULT FALSE"),
            ("twilio_recording_channels", "VARCHAR DEFAULT 'dual'"),
            ("twilio_trim_silence", "BOOLEAN DEFAULT TRUE")
        ]
        
        for col_name, type_def in columns_to_add:
            try:
                logger.info(f"Adding column: {col_name}...")
                await session.execute(text(f"ALTER TABLE agent_configs ADD COLUMN {col_name} {type_def}"))
                logger.info(f"✅ Added {col_name}")
            except Exception as e:
                # Check for "already exists" error in a generic way or just log warning
                err_str = str(e).lower()
                if "already exists" in err_str:
                     logger.warning(f"⚠️ Column {col_name} already exists. Skipping.")
                else:
                     logger.error(f"❌ Error adding {col_name}: {e}")
        
        await session.commit()
        logger.info("🎉 Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_migration())
