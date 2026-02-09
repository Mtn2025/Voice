
import sys
import os
from alembic.config import Config
from alembic.script import ScriptDirectory

def debug_revisions():
    print("🔎 Debugging Alembic Revisions...")
    base_path = os.getcwd()
    ini_path = os.path.join(base_path, "alembic.ini")
    print(f"📂 Config File: {ini_path}")

    config = Config(ini_path)
    try:
        script = ScriptDirectory.from_config(config)
        print("✅ ScriptDirectory loaded.")
        
        print("Walking revisions...")
        for rev in script.walk_revisions():
            print(f"  - {rev.revision} (down: {rev.down_revision})")
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_revisions()
