"""
Database Audit - Phase 1: Inventory
Complete inventory of all 353 columns in AgentConfig.
"""

import csv
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.models import AgentConfig
from sqlalchemy import inspect

def categorize_column(col_name: str) -> str:
    """Categorize column by profile."""
    if col_name in ["id", "name", "created_at", "api_key"]:
        return "meta"
    elif col_name.endswith("_phone"):
        return "phone"
    elif col_name.endswith("_telnyx"):
        return "telnyx"
    elif col_name in [
        "llm_provider", "stt_provider", "tts_provider", "extraction_model",
        "concurrency_limit", "spend_limit_daily", "environment",
        "privacy_mode", "audit_log_enabled",
        "twilio_account_sid", "twilio_auth_token", "twilio_from_number",
        "telnyx_api_key", "telnyx_connection_id"
    ]:
        return "global"
    else:
        return "browser"

def export_inventory():
    """Export complete inventory to CSV."""
    print("=" * 80)
    print("PHASE 1: AgentConfig Inventory")
    print("=" * 80)
    
    # Get all columns from SQLAlchemy model
    mapper = inspect(AgentConfig)
    columns = []
    
    for column in mapper.columns:
        col_name = column.name
        col_type = str(column.type)
        nullable = column.nullable
        default = str(column.default.arg) if column.default else None
        profile = categorize_column(col_name)
        
        columns.append({
            "column_name": col_name,
            "data_type": col_type,
            "nullable": nullable,
            "default_value": default,
            "profile": profile,
            "status": "pending_validation",
            "used_in_schema": "unknown",
            "used_in_frontend": "unknown",
            "notes": ""
        })
    
    # Write to CSV
    output_path = Path("audit/inventory_353_columns.csv")
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            "column_name", "data_type", "nullable", "default_value",
            "profile", "status", "used_in_schema", "used_in_frontend", "notes"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for col in columns:
            writer.writerow(col)
    
    print(f"\n✅ Inventory exported: {output_path}")
    print(f"   Total columns: {len(columns)}")
    
    # Print statistics
    stats = {}
    for col in columns:
        profile = col["profile"]
        stats[profile] = stats.get(profile, 0) + 1
    
    print(f"\n📊 Column Distribution:")
    for profile, count in sorted(stats.items()):
        print(f"   {profile.capitalize()}: {count}")
    
    return columns

if __name__ == "__main__":
    try:
        columns = export_inventory()
        print("\n✅ Phase 1 completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
