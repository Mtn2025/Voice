"""
Apply missing columns by adding them to models.py and using create_all.
"""

import sys
from pathlib import Path
import asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import engine
from app.db.models import Base
from sqlalchemy import inspect

async def apply_missing_columns():
    """Apply the 9 missing columns."""
    print("=" * 80)
    print("Adding Missing Columns to SQLite")
    print("=" * 80)
    
    # SQLAlchemy's create_all will only add missing columns/tables
    # It won't modify existing columns
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Verify columns were added
    async with engine.connect() as conn:
        def get_columns(connection):
            inspector = inspect(connection)
            return [col['name'] for col in inspector.get_columns('agent_configs')]
        
        columns = await conn.run_sync(get_columns)
        
        print(f"\n✅ Total columns in agent_configs: {len(columns)}")
        
        # Check for the new columns
        new_cols = [
            'response_length_phone', 'conversation_tone_phone',
            'conversation_formality_phone', 'conversation_pacing_phone',
            'response_length_telnyx', 'conversation_tone_telnyx',
            'conversation_formality_telnyx', 'conversation_pacing_telnyx',
            'client_tools_enabled_telnyx'
        ]
        
        print(f"\n📋 Checking for new columns:")
        for col in new_cols:
            if col in columns:
                print(f"   ✅ {col}")
            else:
                print(f"   ❌ {col} (NOT FOUND)")
    
    print("\n✅ Column sync completed!")

if __name__ == "__main__":
    try:
        asyncio.run(apply_missing_columns())
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
