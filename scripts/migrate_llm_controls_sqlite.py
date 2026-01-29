"""
Script to apply LLM control fields migration to SQLite database.
Bypasses Alembic for direct SQLite schema update.
"""
import sqlite3
import os

# Find database file
db_path = None
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.db'):
            db_path = os.path.join(root, file)
            print(f"Found DB: {db_path}")
            break
    if db_path:
        break

if not db_path:
    print("❌ No SQLite database found")
    exit(1)

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print(f"\n🗄️  Migrating: {db_path}\n")

# Add 18 new columns for LLM controls
migrations = [
    # Browser Profile (6 campos)
    ("context_window", "INTEGER DEFAULT 10"),
    ("frequency_penalty", "REAL DEFAULT 0.0"),
    ("presence_penalty", "REAL DEFAULT 0.0"),
    ("tool_choice", "TEXT DEFAULT 'auto'"),
    ("dynamic_vars_enabled", "INTEGER DEFAULT 0"),  # Boolean as INTEGER in SQLite
    ("dynamic_vars", "TEXT"),  # JSON as TEXT in SQLite
    
    # Twilio Profile (phone suffix - 6 campos)
    ("context_window_phone", "INTEGER DEFAULT 10"),
    ("frequency_penalty_phone", "REAL DEFAULT 0.0"),
    ("presence_penalty_phone", "REAL DEFAULT 0.0"),
    ("tool_choice_phone", "TEXT DEFAULT 'auto'"),
    ("dynamic_vars_enabled_phone", "INTEGER DEFAULT 0"),
    ("dynamic_vars_phone", "TEXT"),
    
    # Telnyx Profile (telnyx suffix - 6 campos)
    ("context_window_telnyx", "INTEGER DEFAULT 10"),
    ("frequency_penalty_telnyx", "REAL DEFAULT 0.0"),
    ("presence_penalty_telnyx", "REAL DEFAULT 0.0"),
    ("tool_choice_telnyx", "TEXT DEFAULT 'auto'"),
    ("dynamic_vars_enabled_telnyx", "INTEGER DEFAULT 0"),
    ("dynamic_vars_telnyx", "TEXT"),
]

# Check existing columns
cursor.execute("PRAGMA table_info(agent_configs)")
existing_columns = {row[1] for row in cursor.fetchall()}

# Apply migrations
added = 0
skipped = 0

for column_name, column_type in migrations:
    if column_name in existing_columns:
        print(f"⏭️  SKIP: {column_name} (already exists)")
        skipped += 1
    else:
        try:
            sql = f"ALTER TABLE agent_configs ADD COLUMN {column_name} {column_type}"
            cursor.execute(sql)
            print(f"✅ ADD: {column_name}")
            added += 1
        except sqlite3.OperationalError as e:
            print(f"⚠️  ERROR: {column_name} - {e}")

# Commit changes
conn.commit()

print(f"\n📊 Migration Summary:")
print(f"   Added: {added}")
print(f"   Skipped: {skipped}")
print(f"   Total: {added + skipped}/18")

# Verify final schema
cursor.execute("PRAGMA table_info(agent_configs)")
all_columns = cursor.fetchall()
print(f"\n✅ Agent Configs table now has {len(all_columns)} columns")

# Show new columns
new_llm_columns = [col[1] for col in all_columns if any(
    col[1].startswith(prefix) for prefix in ['context_window', 'frequency_penalty', 'presence_penalty', 'tool_choice', 'dynamic_vars']
)]
print(f"✅ LLM Control columns: {len(new_llm_columns)}")
for col in new_llm_columns:
    print(f"   - {col}")

conn.close()
print(f"\n✅ Migration complete!")
