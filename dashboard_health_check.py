import os
import re
import json
import glob
import requests
from collections import defaultdict

# Configuration
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "app", "templates")
PARTIALS_DIR = os.path.join(TEMPLATES_DIR, "partials")
STATIC_JS_DIR = os.path.join(PROJECT_ROOT, "app", "static", "js", "dashboard")
STORE_FILE = os.path.join(STATIC_JS_DIR, "store.v2.js")
DASHBOARD_FILE = os.path.join(TEMPLATES_DIR, "dashboard.html")
REPORT_FILE = "dashboard_health_report.json"
MAP_FILE = "dashboard_controls_map.json"
BASE_URL = "http://localhost:8000"

def parse_store_config_keys():
    """Extracts config keys from store.v2.js for browser, twilio, and telnyx profiles."""
    if not os.path.exists(STORE_FILE):
        print(f"❌ Store file not found: {STORE_FILE}")
        return {}

    with open(STORE_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Regex to capture keys inside initBrowserConfig, initTwilioConfig, initTelnyxConfig
    profiles = {}
    
    for profile in ['browser', 'twilio', 'telnyx']:
        # Find the init function block
        func_name = f"init{profile.capitalize()}Config"
        pattern = re.compile(rf"{func_name}\(\)\s*{{(.*?)}}", re.DOTALL)
        match = pattern.search(content)
        if match:
            block = match.group(1)
            # Find assignments like key: val,
            key_pattern = re.compile(r"\s+([a-zA-Z0-9_]+):")
            keys = key_pattern.findall(block)
            profiles[profile] = set(keys)
        else:
            print(f"⚠️ Could not find {func_name} in store.v2.js")
            profiles[profile] = set()
            
    return profiles

def parse_hidden_inputs():
    """Extracts hidden inputs from dashboard.html and their :value bindings."""
    if not os.path.exists(DASHBOARD_FILE):
        print(f"❌ Dashboard file not found: {DASHBOARD_FILE}")
        return []

    with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Regex for <input type="hidden" ... >
    # Matches <input ... name="..." ... :value="..." ... > in any order
    # Simplified: Find all <input ...> then check attributes
    input_pattern = re.compile(r"<input[^>]*>", re.IGNORECASE)
    hidden_inputs = []
    
    for tag in input_pattern.findall(content):
        if 'type="hidden"' in tag or "type='hidden'" in tag:
            name_match = re.search(r'name=["\']([^"\']+)["\']', tag)
            value_match = re.search(r':value=["\']([^"\']+)["\']', tag)
            
            if name_match and value_match:
                hidden_inputs.append({
                    "name": name_match.group(1),
                    "binding": value_match.group(1)
                })
    
    return hidden_inputs

def parse_partials_controls():
    """Scans partials for x-model bindings."""
    controls = []
    
    partial_files = glob.glob(os.path.join(PARTIALS_DIR, "tab_*.html"))
    partial_files.append(os.path.join(PARTIALS_DIR, "panel_simulator.html"))
    
    for p_file in partial_files:
        filename = os.path.basename(p_file)
        tab_name = filename.replace("tab_", "").replace(".html", "").replace("panel_simulator", "simulator")
        
        with open(p_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Regex to find elements with x-model
        # <(tag) ... x-model="value" ...>
        # This is tricky with regex, but we will assume x-model is distinct
        
        # Find all tags with x-model
        # Group 1: tag name, Group 2: content before x-model, Group 3: model value
        # This is a bit loose but works for standard formatting
        
        # Strategy: Find 'x-model="value"' and then look backwards for the tag name
        # Better: iterate known input tags or just find x-model="..."
        
        model_pattern = re.compile(r'x-model=["\']([^"\']+)["\']')
        
        for i, line in enumerate(content.splitlines()):
            matches = model_pattern.findall(line)
            for model in matches:
                # Guess type from line context
                tag_type = "unknown"
                if "<select" in line: tag_type = "select"
                elif "<textarea" in line: tag_type = "textarea"
                elif "type='checkbox'" in line or 'type="checkbox"' in line: tag_type = "checkbox"
                elif "type='range'" in line or 'type="range"' in line: tag_type = "range"
                elif "<input" in line: tag_type = "input"
                
                controls.append({
                    "tab": tab_name,
                    "file": filename,
                    "type": tag_type,
                    "model": model,
                    "line": i + 1
                })
            
    return controls

def check_endpoints():
    """Checks verify endpoints."""
    endpoints = [
        "/health",
        "/admin/config"
    ]
    status = {}
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=2)
        status["/health"] = "OK" if health.status_code == 200 else f"FAIL {health.status_code}"
    except Exception as e:
        status["/health"] = "UNREACHABLE"

    return status

def generate_map(controls):
    """Generates the dashboard_controls_map.json."""
    controls_map = {"tabs": defaultdict(dict)}
    
    for c in controls:
        tab = c["tab"]
        key = c["model"]
        if "controls" not in controls_map["tabs"][tab]:
            controls_map["tabs"][tab]["controls"] = {}
            
        controls_map["tabs"][tab]["controls"][key] = {
            "type": c["type"],
            "status": "detected",
            "file": c["file"]
        }
        
    return controls_map

def main():
    print("🔍 Starting Dashboard Health Check (Regex Mode)...")
    
    # 1. Parse Store
    store_keys = parse_store_config_keys()
    print(f"✅ Parsed Store: Found {sum(len(k) for k in store_keys.values())} keys across 3 profiles.")
    
    # 2. Parse Hidden Inputs
    hidden_inputs = parse_hidden_inputs()
    print(f"✅ Parsed Dashboard: Found {len(hidden_inputs)} hidden inputs.")
    
    # 3. Parse Visual Controls
    controls = parse_partials_controls()
    print(f"✅ Parsed Partials: Found {len(controls)} visual controls.")
    
    # 4. Analyze Bindings
    report = {
        "orphaned_controls": [],
        "missing_hidden_inputs": [],
        "summary": {
            "total_controls": len(controls),
            "store_keys": sum(len(k) for k in store_keys.values())
        }
    }
    
    all_store_keys = set().union(*store_keys.values())
    
    for ctrl in controls:
        model = ctrl["model"]
        is_orphan = False
        
        # Logic to check if model exists in store
        if model.startswith("c."):
            key = model.split(".")[1]
            if key not in all_store_keys:
                is_orphan = True
        elif model.startswith("configs."):
            parts = model.split(".")
            if len(parts) == 3:
                profile = parts[1]
                key = parts[2]
                if profile in store_keys and key not in store_keys[profile]:
                    is_orphan = True
        
        if is_orphan:
            report["orphaned_controls"].append(ctrl)

    # Check Connectivity
    endpoints_status = check_endpoints()
    
    # Generate Map
    controls_map = generate_map(controls)
    
    # Save Outputs
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(controls_map, f, indent=2)
        
    print(f"\n📄 Generated {REPORT_FILE}")
    print(f"📄 Generated {MAP_FILE}")
    print(f"📊 Endpoint Status: {json.dumps(endpoints_status, indent=2)}")

if __name__ == "__main__":
    main()
