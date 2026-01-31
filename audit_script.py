"""
Comprehensive audit script to extract and analyze all configuration fields
from the codebase: UI, Schema, and Orchestrator.
"""
import re
import ast
from pathlib import Path
from typing import List, Dict, Set
import csv

# Paths
BASE_DIR = Path(__file__).parent
DASHBOARD_HTML = BASE_DIR / "app" / "templates" / "dashboard.html"
MODELS_PY = BASE_DIR / "app" / "db" / "models.py"
ORCHESTRATOR_PY = BASE_DIR / "app" / "core" / "orchestrator_v2.py"  # Updated: orchestrator.py no longer exists
OUTPUT_DIR = BASE_DIR  # Output to project root instead of hardcoded conversation dir

def extract_ui_fields(html_path: Path) -> List[Dict]:
    """Extract all x-model bindings from dashboard.html"""
    print(f"[1/5] Analyzing UI fields from {html_path.name}...")
    content = html_path.read_text(encoding='utf-8')
    
    # Regex to find x-model="c.FIELD_NAME"
    pattern = r'x-model="c\.(\w+)"'
    matches = re.findall(pattern, content)
    
    fields = []
    for field in set(matches):  # Unique fields only
        # Find line number
        lines = content.split('\n')
        line_num = next((i+1 for i, line in enumerate(lines) if f'x-model="c.{field}"' in line), None)
        fields.append({'field': field, 'source': 'UI', 'line': line_num})
    
    print(f"   Found {len(fields)} unique x-model bindings")
    return fields

def extract_schema_fields(models_path: Path) -> List[Dict]:
    """Extract all Column definitions from models.py AgentConfig class"""
    print(f"\n[2/5] Analyzing schema fields from {models_path.name}...")
    content = models_path.read_text(encoding='utf-8')
    
    # Find AgentConfig class
    class_match = re.search(r'class AgentConfig\(Base\):(.*?)(?=\nclass |\Z)', content, re.DOTALL)
    if not class_match:
        print("   ERROR: AgentConfig class not found!")
        return []
    
    class_content = class_match.group(1)
    
    # Find all column definitions
    # Pattern: field_name = Column(Type, ...)
    pattern = r'^\s+(\w+)\s*=\s*Column\('
    fields = []
    
    for i, line in enumerate(class_content.split('\n'), 1):
        match = re.match(pattern, line)
        if match:
            field_name = match.group(1)
            # Extract type
            type_match = re.search(r'Column\((\w+)', line)
            field_type = type_match.group(1) if type_match else 'Unknown'
            # Extract default
            default_match = re.search(r'default=([^,)]+)', line)
            default_value = default_match.group(1) if default_match else 'None'
            
            fields.append({
                'field': field_name,
                'source': 'Schema',
                'type': field_type,
                'default': default_value.strip('"').replace('\\n', ' ')[:50]  # Truncate
            })
    
    print(f"   Found {len(fields)} Column definitions")
    return fields

def extract_alpine_init_fields(html_path: Path) -> Dict[str, List[str]]:
    """Extract field assignments from initBrowserConfig, initTwilioConfig, initTelnyxConfig"""
    print(f"\n[3/5] Analyzing Alpine.js init functions from {html_path.name}...")
    content = html_path.read_text(encoding='utf-8')
    
    results = {}
    
    for func_name in ['initBrowserConfig', 'initTwilioConfig', 'initTelnyxConfig']:
        # Find function body
        pattern = rf'{func_name}\(\)\s*{{(.*?)}}'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            func_body = match.group(1)
            # Find all assignments like: field: s.backend_field
            assignments = re.findall(r'(\w+):\s*s\.(\w+)', func_body)
            results[func_name] = assignments
            print(f"   {func_name}: Found {len(assignments)} field mappings")
    
    return results

def extract_orchestrator_usage(orch_path: Path, schema_fields: List[Dict]) -> List[Dict]:
    """Check which schema fields are actually used in orchestrator"""
    print(f"\n[4/5] Analyzing orchestrator usage from {orch_path.name}...")
    content = orch_path.read_text(encoding='utf-8')
    
    usage = []
    for schema_field in schema_fields:
        field_name = schema_field['field']
        # Search for self.config.FIELD_NAME
        pattern = rf'self\.config\.{field_name}\b'
        matches = re.findall(pattern, content)
        
        if matches:
            usage.append({
                'field': field_name,
                'used_in_orchestrator': True,
                'usage_count': len(matches)
            })
    
    print(f"   Found {len(usage)} schema fields used in orchestrator")
    return usage

def generate_reconciliation_report(ui_fields, schema_fields, alpine_init, orch_usage, output_dir: Path):
    """Generate comprehensive reconciliation CSV"""
    print(f"\n[5/5] Generating reconciliation report...")
    
    # Create sets for quick lookup
    ui_fields_set = {f['field'] for f in ui_fields}
    schema_fields_dict = {f['field']: f for f in schema_fields}
    orch_usage_dict = {f['field']: f for f in orch_usage}
    
    # Collect all unique field names
    all_fields = ui_fields_set | schema_fields_dict.keys()
    
    # Build reconciliation rows
    rows = []
    for field in sorted(all_fields):
        row = {
            'field_name': field,
            'in_ui': '✓' if field in ui_fields_set else '✗',
            'in_schema': '✓' if field in schema_fields_dict else '✗',
            'schema_type': schema_fields_dict[field]['type'] if field in schema_fields_dict else 'N/A',
            'schema_default': schema_fields_dict[field]['default'] if field in schema_fields_dict else 'N/A',
            'used_in_orchestrator': '✓' if field in orch_usage_dict else '✗',
            'usage_count': orch_usage_dict[field]['usage_count'] if field in orch_usage_dict else 0,
        }
        
        # Determine status
        if field in ui_fields_set and field in schema_fields_dict:
            row['status'] = 'OK'
        elif field in ui_fields_set and field not in schema_fields_dict:
            row['status'] = '⚠️ MISSING_SCHEMA'
        elif field not in ui_fields_set and field in schema_fields_dict:
            row['status'] = 'ℹ️ MISSING_UI'
        else:
            row['status'] = '❌ UNKNOWN'
        
        rows.append(row)
    
    # Write CSV
    output_file = output_dir / "reconciliation_report.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"   ✅ Report saved to: {output_file}")
    
    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total unique fields: {len(all_fields)}")
    print(f"Fields in UI: {len(ui_fields_set)}")
    print(f"Fields in Schema: {len(schema_fields_dict)}")
    print(f"Fields used in Orchestrator: {len(orch_usage_dict)}")
    print(f"\nDiscrepancies:")
    missing_schema = [r for r in rows if r['status'] == '⚠️ MISSING_SCHEMA']
    missing_ui = [r for r in rows if r['status'] == 'ℹ️ MISSING_UI']
    print(f"  ⚠️ Missing in Schema: {len(missing_schema)}")
    if missing_schema:
        for r in missing_schema[:10]:  # Show first 10
            print(f"     - {r['field_name']}")
    print(f"  ℹ️ Missing in UI: {len(missing_ui)}")
    if missing_ui:
        for r in missing_ui[:10]:  # Show first 10
            print(f"     - {r['field_name']}")

def main():
    print("="*60)
    print("COMPREHENSIVE CONFIGURATION AUDIT")
    print("="*60)
    
    # Extract data
    ui_fields = extract_ui_fields(DASHBOARD_HTML)
    schema_fields = extract_schema_fields(MODELS_PY)
    alpine_init = extract_alpine_init_fields(DASHBOARD_HTML)
    orch_usage = extract_orchestrator_usage(ORCHESTRATOR_PY, schema_fields)
    
    # Generate report
    generate_reconciliation_report(ui_fields, schema_fields, alpine_init, orch_usage, OUTPUT_DIR)
    
    print(f"\n{'='*60}")
    print("AUDIT COMPLETE")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
