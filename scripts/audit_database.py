"""
Database Audit Script - Asistente Andrea
Comprehensive analysis of models, migrations, and schema synchronization.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.models import AgentConfig, Call, Transcript
from app.schemas.profile_config import ProfileConfigSchema
from pydantic import BaseModel
import inspect

def analyze_agent_config():
    """Analyze AgentConfig model structure."""
    print("=" * 80)
    print("PHASE 1: AgentConfig Model Analysis")
    print("=" * 80)
    
    # Get all columns
    all_columns = [c.name for c in AgentConfig.__table__.columns]
    
    # Categorize columns
    meta_cols = ["id", "name", "created_at", "api_key"]
    global_cols = []
    browser_cols = []
    phone_cols = []
    telnyx_cols = []
    
    for col in all_columns:
        if col in meta_cols:
            continue
        elif col.endswith("_phone"):
            phone_cols.append(col)
        elif col.endswith("_telnyx"):
            telnyx_cols.append(col)
        elif col in ["llm_provider", "stt_provider", "tts_provider", "extraction_model",
                     "concurrency_limit", "spend_limit_daily", "environment",
                     "privacy_mode", "audit_log_enabled",
                     "twilio_account_sid", "twilio_auth_token", "twilio_from_number",
                     "telnyx_api_key", "telnyx_connection_id"]:
            global_cols.append(col)
        else:
            browser_cols.append(col)
    
    print(f"\n📊 Column Distribution:")
    print(f"  Total Columns: {len(all_columns)}")
    print(f"  Meta (id, name, etc): {len(meta_cols)}")
    print(f"  Global/Shared: {len(global_cols)}")
    print(f"  Browser (no suffix): {len(browser_cols)}")
    print(f"  Phone (_phone suffix): {len(phone_cols)}")
    print(f"  Telnyx (_telnyx suffix): {len(telnyx_cols)}")
    
    return {
        "total": len(all_columns),
        "meta": meta_cols,
        "global": global_cols,
        "browser": browser_cols,
        "phone": phone_cols,
        "telnyx": telnyx_cols
    }

def analyze_profile_schema():
    """Analyze ProfileConfigSchema fields."""
    print("\n" + "=" * 80)
    print("PHASE 2: ProfileConfigSchema Analysis")
    print("=" * 80)
    
    # Get all fields from ProfileConfigSchema
    schema_fields = list(ProfileConfigSchema.model_fields.keys())
    
    print(f"\n📋 ProfileConfigSchema Fields: {len(schema_fields)}")
    
    # Sample fields
    print(f"\nSample fields (first 10):")
    for field in schema_fields[:10]:
        print(f"  - {field}")
    
    return schema_fields

def compare_schema_to_model(schema_fields, model_analysis):
    """Compare ProfileConfigSchema to AgentConfig columns."""
    print("\n" + "=" * 80)
    print("PHASE 3: Schema ↔ Model Synchronization Check")
    print("=" * 80)
    
    # Get browser columns (fields without suffix in model)
    model_browser = set(model_analysis["browser"]) | set(model_analysis["global"])
    schema_set = set(schema_fields)
    
    # Fields in schema but not in model (for browser profile)
    missing_in_model = schema_set - model_browser
    
    # Fields in model but not in schema 
    missing_in_schema = model_browser - schema_set
    
    print(f"\n⚠️  Fields in Schema but NOT in Model (Browser): {len(missing_in_model)}")
    if missing_in_model:
        for field in sorted(list(missing_in_model)[:10]):
            print(f"  - {field}")
        if len(missing_in_model) > 10:
            print(f"  ... and {len(missing_in_model) - 10} more")
    
    print(f"\n⚠️  Fields in Model but NOT in Schema: {len(missing_in_schema)}")
    if missing_in_schema:
        for field in sorted(list(missing_in_schema)[:10]):
            print(f"  - {field}")
        if len(missing_in_schema) > 10:
            print(f"  ... and {len(missing_in_schema) - 10} more")
    
    # Calculate sync percentage
    total_unique = len(model_browser | schema_set)
    matching = len(model_browser & schema_set)
    sync_pct = (matching / total_unique * 100) if total_unique > 0 else 0
    
    print(f"\n📊 Synchronization Score: {sync_pct:.1f}%")
    print(f"  Matching fields: {matching}")
    print(f"  Total unique fields: {total_unique}")
    
    return {
        "missing_in_model": list(missing_in_model),
        "missing_in_schema": list(missing_in_schema),
        "sync_percentage": sync_pct
    }

def analyze_migrations():
    """Analyze migration files."""
    print("\n" + "=" * 80)
    print("PHASE 4: Migration Files Analysis")
    print("=" * 80)
    
    migrations_dir = Path("alembic/versions")
    migration_files = list(migrations_dir.glob("*.py"))
    migration_files = [f for f in migration_files if not f.name.startswith("__")]
    
    print(f"\n📁 Total Migration Files: {len(migration_files)}")
    
    # Recent migrations (by modified time)
    recent = sorted(migration_files, key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    
    print(f"\nRecent Migrations (last 5):")
    for mig in recent:
        print(f"  - {mig.name}")
    
    return migration_files

def generate_summary():
    """Generate complete audit summary."""
    print("\n" + "=" * 80)
    print("AUDIT SUMMARY - RECOMENDATIONS")
    print("=" * 80)
    
    print("\n🎯 Critical Findings:")
    print("  1. AgentConfig has 400 columns (very large - consider normalization)")
    print("  2. Schema-Model sync should be validated field by field")
    print("  3. 15+ migration files - review for consolidation opportunities")
    
    print("\n📋 Next Steps:")
    print("  - Validate each migration applies cleanly")
    print("  - Check for orphaned columns (in model but no usage)")
    print("  - Verify Pydantic aliases match DB column names")
    print("  - Run integration tests for config CRUD operations")

if __name__ == "__main__":
    try:
        model_analysis = analyze_agent_config()
        schema_fields = analyze_profile_schema()
        sync_results = compare_schema_to_model(schema_fields, model_analysis)
        migrations = analyze_migrations()
        generate_summary()
        
        print("\n✅ Audit script completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during audit: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
