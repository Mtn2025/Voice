"""Check DB directly for system_prompt_telnyx"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/assistant_db")
engine = create_engine(DATABASE_URL.replace("postgresql+asyncpg", "postgresql"))

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            system_prompt_telnyx,
            llm_provider_telnyx,
            llm_model_telnyx,
            temperature_telnyx
        FROM agent_configs 
        WHERE name='default'
    """))
    
    row = result.fetchone()
    
    print("="*80)
    print("DB Values for Telnyx Profile:")
    print("="*80)
    print(f"system_prompt_telnyx: {row[0]}")
    print(f"llm_provider_telnyx: {row[1]}")
    print(f"llm_model_telnyx: {row[2]}")
    print(f"temperature_telnyx: {row[3]}")
    print("="*80)

engine.dispose()
