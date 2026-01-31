"""
Quick script to verify and apply missing columns to local SQLite database.
"""

import sys
from pathlib import Path
import os

# Force SQLite environment
os.environ["DATABASE_URL"] = "sqlite:///./data/calls.db"

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from app.db.database import init_db
from app.db.models import Base, AgentConfig
from sqlalchemy import inspect, select
from app.db.database import get_async_session

async def verify_columns():
    """Verify that columns were added successfully."""
    print("=" * 80)
    print("Verifying Database Columns (SQLite)")
    print("=" * 80)
    
    # Initialize database (creates all tables according to current models.py)
    await init_db()
    
    # Verify columns exist
    async for session in get_async_session():
        async with session.begin():
            result = await session.execute(select(AgentConfig).limit(1))
            config = result.scalar_one_or_none()
            
            # Check for new columns
            new_columns = [
                'response_length_phone', 'conversation_tone_phone',
                'conversation_formality_phone', 'conversation_pacing_phone',
                'response_length_telnyx', 'conversation_tone_telnyx',
                'conversation_formality_telnyx', 'conversation_pacing_telnyx',
                'client_tools_enabled_telnyx'
            ]
            
            print(f"\n📋 Checking for 9 new columns:")
            found = 0
            for col in new_columns:
                if hasattr(AgentConfig, col):
                    print(f"   ✅ {col} (exists in model)")
                    found += 1
                else:
                    print(f"   ❌ {col} (NOT in model)")
            
            print(f"\n📊 Result: {found}/9 columns found")
            
            if found == 9:
                print(f"\n✅ SUCCESS! All 9 columns added to database.")
            else:
                print(f"\n⚠️  WARNING: Only {found}/9 columns found.")
        
        break  # Only need one session
    
    print("\n✅ Verification completed!")

if __name__ == "__main__":
    try:
        asyncio.run(verify_columns())
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
