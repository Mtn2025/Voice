"""
Apply missing columns migration to SQLite directly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import engine
from app.db.models import Base
from sqlalchemy import inspect, text

def apply_missing_columns():
    """Apply the 9 missing columns to SQLite database."""
    print("=" * 80)
    print("Applying Missing Columns Migration (SQLite)")
    print("=" * 80)
    
    with engine.connect() as conn:
        inspector = inspect(conn)
        existing_cols = {col['name'] for col in inspector.get_columns('agent_configs')}
        
        # Define columns to add
        columns_to_add = [
            # Phone Profile - Conversation Style (4)
            ("response_length_phone", "VARCHAR(50)"),
            ("conversation_tone_phone", "VARCHAR(50)"),
            ("conversation_formality_phone", "VARCHAR(50)"),
            ("conversation_pacing_phone", "VARCHAR(50)"),
            
            # Telnyx Profile - Conversation Style (4)
            ("response_length_telnyx", "VARCHAR(50)"),
            ("conversation_tone_telnyx", "VARCHAR(50)"),
            ("conversation_formality_telnyx", "VARCHAR(50)"),
            ("conversation_pacing_telnyx", "VARCHAR(50)"),
            
            # Telnyx Profile - Tools (1)
            ("client_tools_enabled_telnyx", "BOOLEAN DEFAULT 0"),
        ]
        
        added = 0
        skipped = 0
        
        for col_name, col_type in columns_to_add:
            if col_name in existing_cols:
                print(f"   ⏭️  Skipped (already exists): {col_name}")
                skipped += 1
            else:
                try:
                    sql = f"ALTER TABLE agent_configs ADD COLUMN {col_name} {col_type}"
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"   ✅ Added: {col_name} ({col_type})")
                    added += 1
                except Exception as e:
                    print(f"   ❌ Error adding {col_name}: {e}")
        
        print(f"\n📊 Results:")
        print(f"   Added: {added}")
        print(f"   Skipped: {skipped}")
        print(f"   Total: {added + skipped}/9")
        
        # Verify
        inspector_after = inspect(conn)
        final_cols = {col['name'] for col in inspector_after.get_columns('agent_configs')}
        
        print(f"\n✅ Final column count: {len(final_cols)}")
        
        return added

if __name__ == "__main__":
    try:
        added = apply_missing_columns()
        if added > 0:
            print("\n✅ Migration applied successfully!")
        else:
            print("\n⏭️  All columns already existed.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
