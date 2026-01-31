"""
Obsolete Columns Review Script
Analyzes code usage of 163 obsolete columns to recommend actions.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def load_obsolete_columns():
    """Load obsolete columns from classification."""
    with open("audit/columns_classified.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get("obsolete", [])

def search_column_usage(column_name: str, search_paths: list) -> dict:
    """Search for column usage in codebase."""
    import subprocess
    
    results = {
        "column": column_name,
        "found_in": [],
        "references": 0
    }
    
    # Search in specific directories
    for search_dir in search_paths:
        try:
            # Use ripgrep for fast searching
            cmd = ["rg", "-i", "-l", column_name, str(search_dir)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and result.stdout.strip():
                files = result.stdout.strip().split('\n')
                results["found_in"].extend(files)
                results["references"] += len(files)
        except Exception:
            # Fallback: manual search
            pass
    
    return results

def classify_column(column_data: dict, usage: dict) -> str:
    """Classify column based on usage."""
    column_name = column_data["column"]
    
    # Check if used in code
    if usage["references"] > 0:
        # Check if it's in critical files
        critical_files = ["models.py", "config_utils.py", "orchestrator.py", "base.py"]
        for file in usage["found_in"]:
            if any(cf in file for cf in critical_files):
                return "MANTENER"
        
        return "DOCUMENTAR"
    
    # Not found in code
    return "ELIMINAR"

def analyze_obsolete_columns():
    """Analyze all obsolete columns."""
    print("=" * 80)
    print("OBSOLETE COLUMNS REVIEW")
    print("=" * 80)
    
    obsolete_cols = load_obsolete_columns()
    
    print(f"\n📊 Total obsolete columns: {len(obsolete_cols)}")
    
    # Search paths
    search_paths = [
        Path("app"),
        Path("tests")
    ]
    
    results = {
        "ELIMINAR": [],
        "MANTENER": [],
        "DOCUMENTAR": []
    }
    
    print(f"\n🔍 Analyzing usage in codebase...")
    
    for i, col_data in enumerate(obsolete_cols, 1):
        column_name = col_data["column"]
        
        if i % 10 == 0:
            print(f"   Progress: {i}/{len(obsolete_cols)}")
        
        # Search for usage
        usage = search_column_usage(column_name, search_paths)
        
        # Classify
        classification = classify_column(col_data, usage)
        
        results[classification].append({
            **col_data,
            "usage": usage
        })
    
    print(f"\n✅ Analysis complete!")
    print(f"\n📊 Classification Results:")
    print(f"   ELIMINAR (no usage): {len(results['ELIMINAR'])}")
    print(f"   MANTENER (in critical files): {len(results['MANTENER'])}")
    print(f"   DOCUMENTAR (in non-critical): {len(results['DOCUMENTAR'])}")
    
    # Export results
    output_path = Path("audit/obsolete_columns_review.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results exported: {output_path}")
    
    return results

if __name__ == "__main__":
    try:
        results = analyze_obsolete_columns()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
