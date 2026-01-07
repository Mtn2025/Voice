import asyncio
from sqlalchemy import text
from app.db.database import engine

async def check_config():
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT 
                first_message_telnyx,
                first_message,
                llm_provider_telnyx,
                stt_provider_telnyx,
                voice_name_telnyx
            FROM agent_configs 
            LIMIT 1
        """))
        row = result.fetchone()
        if row:
            print("Config Telnyx:")
            print(f"  first_message_telnyx: {row[0]}")
            print(f"  first_message (default): {row[1]}")
            print(f"  llm_provider_telnyx: {row[2]}")
            print(f"  stt_provider_telnyx: {row[3]}")
            print(f"  voice_name_telnyx: {row[4]}")
        else:
            print("No config found!")

asyncio.run(check_config())
