
import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text

async def patch():
    async with AsyncSessionLocal() as session:
        print("Patched DB: Adding Telnyx columns...")
        columns = [
            ("stt_provider_telnyx", "VARCHAR DEFAULT 'azure'"),
            ("stt_language_telnyx", "VARCHAR DEFAULT 'es-MX'"),
            ("llm_provider_telnyx", "VARCHAR DEFAULT 'groq'"),
            ("llm_model_telnyx", "VARCHAR DEFAULT 'llama-3.3-70b-versatile'"),
            ("system_prompt_telnyx", "TEXT DEFAULT NULL"),
            ("voice_name_telnyx", "VARCHAR DEFAULT 'es-MX-DaliaNeural'"),
            ("voice_style_telnyx", "VARCHAR DEFAULT NULL"),
            ("temperature_telnyx", "FLOAT DEFAULT 0.7"),
            ("first_message_telnyx", "VARCHAR DEFAULT 'Hola, soy Andrea de Ubrokers. ¿Me escucha bien?'"),
            ("first_message_mode_telnyx", "VARCHAR DEFAULT 'speak-first'"),
            ("max_tokens_telnyx", "INTEGER DEFAULT 250"),
            ("initial_silence_timeout_ms_telnyx", "INTEGER DEFAULT 5000"),
            ("input_min_characters_telnyx", "INTEGER DEFAULT 4"),
            ("enable_denoising_telnyx", "BOOLEAN DEFAULT TRUE"),
            ("voice_pacing_ms_telnyx", "INTEGER DEFAULT 500"),
            ("silence_timeout_ms_telnyx", "INTEGER DEFAULT 1200"),
            ("interruption_threshold_telnyx", "INTEGER DEFAULT 2"),
            ("hallucination_blacklist_telnyx", "VARCHAR DEFAULT 'Pero.,Y...,Mm.,Oye.,Ah.'"),
            ("voice_speed_telnyx", "FLOAT DEFAULT 0.9")
        ]

        for col, dtype in columns:
            try:
                print(f"Adding {col}...")
                await session.execute(text(f"ALTER TABLE agent_configs ADD COLUMN {col} {dtype}"))
                await session.commit()
                print(f"✅ Added {col}")
            except Exception as e:
                print(f"⚠️ Error adding {col} (maybe exists): {e}")

if __name__ == "__main__":
    asyncio.run(patch())
