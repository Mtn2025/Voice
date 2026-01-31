"""
Database Audit - Phase 3: Classification
Classify all 353 columns into 4 categories.
"""

import csv
import json
import sys
from pathlib import Path

def load_inventory():
    """Load inventory CSV."""
    inventory_path = Path("audit/inventory_353_columns.csv")
    columns = {}
    
    with open(inventory_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            columns[row['column_name']] = row
    
    return columns

def load_schema_mapping():
    """Load schema mapping JSON."""
    mapping_path = Path("audit/schema_to_model_mapping.json")
    
    with open(mapping_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def classify_columns():
    """Classify all columns."""
    print("=" * 80)
    print("PHASE 3: Column Classification")
    print("=" * 80)
    
    inventory = load_inventory()
    schema_mapping = load_schema_mapping()
    
    # Categories
    valid = []
    missing = []
    obsolete = []
    
    # Get all columns that are in schemas
    schema_columns = set()
    for profile_data in schema_mapping.values():
        for item in profile_data['matched']:
            schema_columns.add(item['db_column'])
        for item in profile_data['schema_only']:
            schema_columns.add(item['expected_db_column'])
    
    # Classify each column
    for col_name, col_data in inventory.items():
        # Skip meta columns
        if col_data['profile'] == 'meta':
            continue
        
        # Check if in schema
        in_schema = col_name in schema_columns
        
        if in_schema:
            # Column exists in both DB and Schema
            valid.append({
                "column": col_name,
                "profile": col_data['profile'],
                "type": col_data['data_type'],
                "status": "VALID"
            })
        else:
            # Column exists in DB but NOT in schema
            obsolete.append({
                "column": col_name,
                "profile": col_data['profile'],
                "type": col_data['data_type'],
                "status": "OBSOLETE",
                "recommendation": "Review if still needed, or remove from DB"
            })
    
    # Add missing columns (in schema but not in DB)
    for profile_name, profile_data in schema_mapping.items():
        for item in profile_data['schema_only']:
            missing.append({
                "schema_field": item['schema_field'],
                "alias": item['alias'],
                "expected_db_column": item['expected_db_column'],
                "profile": profile_name,
                "status": "MISSING",
                "recommendation": "CREATE MIGRATION to add column"
            })
    
    # Print results
    print(f"\n📊 Classification Results:")
    print(f"   ✅ Valid (in schema + in DB): {len(valid)}")
    print(f"   🔴 Missing (in schema, not in DB): {len(missing)}")
    print(f"   ❌ Obsolete (in DB, not in schema): {len(obsolete)}")
    
    print(f"\n🔴 Missing Columns ({len(missing)}):")
    for item in missing:
        print(f"   - {item['expected_db_column']} ({item['profile']})")
    
    if obsolete:
        print(f"\n❌ Obsolete Columns (first 10):")
        for item in obsolete[:10]:
            print(f"   - {item['column']} ({item['profile']})")
    
    # Export results
    results = {
        "valid": valid,
        "missing": missing,
        "obsolete": obsolete
    }
    
    output_path = Path("audit/columns_classified.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Classification exported: {output_path}")
    
    return results

if __name__ == "__main__":
    try:
        results = classify_columns()
        print("\n✅ Phase 3 completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
