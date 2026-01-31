"""
Script to apply Voice/TTS control fields migration to SQLite database.
Bypasses Alembic for direct SQLite schema update.
"""
import os
import sqlite3
import sys

# Find database file
db_path = None
for root, _dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.db'):
            db_path = os.path.join(root, file)
            print(f"Found DB: {db_path}")
            break
    if db_path:
        break

if not db_path:
    print("❌ No SQLite database found")
    sys.exit(1)

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print(f"\n🗄️  Migrating: {db_path} (TTS Controls v2)\n")

# Fields definition (Column Name, SQLite Type)
new_fields = [
    # ElevenLabs
    ("voice_stability", "REAL DEFAULT 0.5"),
    ("voice_similarity_boost", "REAL DEFAULT 0.75"),
    ("voice_style_exaggeration", "REAL DEFAULT 0.0"),
    ("voice_speaker_boost", "INTEGER DEFAULT 1"), # Boolean 1
    ("voice_multilingual", "INTEGER DEFAULT 1"), # Boolean 1

    # Technical
    ("tts_latency_optimization", "INTEGER DEFAULT 0"),
    ("tts_output_format", "TEXT DEFAULT 'pcm_16000'"),

    # Humanization
    ("voice_filler_injection", "INTEGER DEFAULT 0"), # Boolean 0
    ("voice_backchanneling", "INTEGER DEFAULT 0"), # Boolean 0
    ("text_normalization_rule", "TEXT DEFAULT 'auto'"),
    ("pronunciation_dictionary", "TEXT"), # JSON string
]

suffixes = ["", "_phone", "_telnyx"]
migrations = []

for suffix in suffixes:
    for field_name, field_type in new_fields:
        full_name = f"{field_name}{suffix}"

        # Phone specific defaults adjustments
        final_type = field_type
        if "pcm_16000" in field_type and suffix != "":
            final_type = "TEXT DEFAULT 'pcm_8000'"

        migrations.append((full_name, final_type))

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

print("\n📊 Migration Summary:")
print(f"   Added: {added}")
print(f"   Skipped: {skipped}")
print(f"   Total: {added + skipped}/{len(migrations)}")

# Verify final schema
cursor.execute("PRAGMA table_info(agent_configs)")
all_columns = cursor.fetchall()
print(f"\n✅ Agent Configs table now has {len(all_columns)} columns")

conn.close()
print("\n✅ TTS Migration complete!")
