"""
Database Audit - Phase 2: Schema to Model Mapping
Maps ProfileConfigSchema fields to AgentConfig columns.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.models import AgentConfig
from app.schemas.profile_config import ProfileConfigSchema
from app.schemas.browser_schemas import BrowserConfigUpdate
from app.schemas.twilio_schemas import TwilioConfigUpdate
from app.schemas.telnyx_schemas import TelnyxConfigUpdate
from sqlalchemy import inspect

def get_db_columns():
    """Get all column names from AgentConfig."""
    mapper = inspect(AgentConfig)
    return {col.name for col in mapper.columns}

def analyze_schema_mapping(schema_class, profile_name: str, db_columns: set):
    """Analyze mapping for a specific schema/profile."""
    print(f"\n📋 Analyzing {profile_name} Profile...")
    
    mappings = {
        "matched": [],
        "schema_only": [],
        "issues": []
    }
    
    # Get all fields from schema
    schema_fields = schema_class.model_fields
    
    for field_name, field_info in schema_fields.items():
        # Get the alias (camelCase frontend name)
        alias = field_info.alias if field_info.alias else field_name
        
        # The field_name in schema ALREADY includes the suffix (_phone, _telnyx, or none for browser)
        # So we just check directly
        expected_db_column = field_name
        
        # Check if column exists in DB
        if expected_db_column in db_columns:
            mappings["matched"].append({
                "schema_field": field_name,
                "alias": alias,
                "db_column": expected_db_column,
                "match": True
            })
        else:
            mappings["schema_only"].append({
                "schema_field": field_name,
                "alias": alias,
                "expected_db_column": expected_db_column,
                "match": False,
                "issue": "MISSING_COLUMN"
            })
    
    print(f"   ✅ Matched: {len(mappings['matched'])}")
    print(f"   ⚠️  Schema only (no DB column): {len(mappings['schema_only'])}")
    
    if mappings['schema_only']:
        print(f"\n   Missing columns sample (first 5):")
        for item in mappings['schema_only'][:5]:
            print(f"      - {item['schema_field']} (DB column expected: {item['expected_db_column']})")
    
    return mappings

def run_phase2():
    """Execute Phase 2: Schema to Model mapping."""
    print("=" * 80)
    print("PHASE 2: Schema → Model Mapping")
    print("=" * 80)
    
    # Get all DB columns
    db_columns = get_db_columns()
    print(f"\n📊 Total DB columns: {len(db_columns)}")
    
    # Analyze each profile
    results = {}
    
    # Browser (field names have no suffix)
    results["browser"] = analyze_schema_mapping(
        BrowserConfigUpdate, "Browser", db_columns
    )
    
    # Phone (field names already have _phone suffix)
    results["phone"] = analyze_schema_mapping(
        TwilioConfigUpdate, "Phone/Twilio", db_columns
    )
    
    # Telnyx (field names already have _telnyx suffix)
    results["telnyx"] = analyze_schema_mapping(
        TelnyxConfigUpdate, "Telnyx", db_columns
    )
    
    # Export to JSON
    output_path = Path("audit/schema_to_model_mapping.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Mapping exported: {output_path}")
    
    # Summary statistics
    total_matched = sum(len(r["matched"]) for r in results.values())
    total_missing = sum(len(r["schema_only"]) for r in results.values())
    total_fields = total_matched + total_missing
    
    sync_pct = (total_matched / total_fields * 100) if total_fields > 0 else 0
    
    print(f"\n📊 Overall Synchronization:")
    print(f"   Matched: {total_matched}")
    print(f"   Missing in DB: {total_missing}")
    print(f"   Sync Rate: {sync_pct:.1f}%")
    
    return results

if __name__ == "__main__":
    try:
        results = run_phase2()
        print("\n✅ Phase 2 completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
