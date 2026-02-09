import asyncio
from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

def check_columns():
    """Check which stt_silence columns exist in DB"""
    engine = create_engine(str(settings.DATABASE_URL).replace('asyncpg', 'psycopg2'))
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='agent_configs' 
            AND (column_name LIKE '%stt_silence%' OR column_name LIKE '%vad_threshold%')
            ORDER BY column_name
        """))
        
        columns = [row[0] for row in result]
        print("Columns in DB:")
        for col in columns:
            print(f"  - {col}")
        
        return columns

if __name__ == "__main__":
    cols = check_columns()
    
    # Check if missing
    required = ['stt_silence_timeout_telnyx', 'vad_threshold_telnyx']
    missing = [c for c in required if c not in cols]
    
    if missing:
        print(f"\n❌ MISSING: {missing}")
    else:
        print(f"\n✅ All columns exist")
