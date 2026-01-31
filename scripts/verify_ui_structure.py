
import os
import re
import sys

# Add project root to path to allow importing 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas.config_schemas import BrowserConfigUpdate, TelnyxConfigUpdate, TwilioConfigUpdate

# Configuration
TEMPLATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app/templates/partials"))

# Mapping Schemas to Expected Tabs
SCHEMA_TAB_MAPPING = {
    "BrowserConfigUpdate": ["tab_model.html", "tab_voice.html", "tab_transcriber.html", "tab_system.html", "tab_advanced.html", "tab_analysis.html"],
    "TwilioConfigUpdate": ["tab_connectivity.html", "tab_voice.html", "tab_transcriber.html", "tab_advanced.html"], # Phones often share Model/Advanced
    "TelnyxConfigUpdate": ["tab_connectivity.html", "tab_voice.html", "tab_transcriber.html", "tab_advanced.html", "tab_system.html"],
    # Core is distributed
}

def get_schema_fields(schema_cls):
    """Extracts (alias, field_name) tuples from a Pydantic schema."""
    fields = []
    for name, info in schema_cls.model_fields.items():
        alias = info.alias or name
        fields.append((alias, name))
    return fields

def scan_templates_for_binding(binding_name):
    """Scans all partials for x-model="c.binding_name" or similar."""
    # We look for 'c.ALIAS' or 'serverConfig.ALIAS' or purely 'ALIAS' in some contexts
    # The standard in store.v2.js is 'c.alias'.

    found_in = []

    regex = re.compile(rf'x-model=["\'].*?\b{re.escape(binding_name)}\b.*?["\']')

    for filename in os.listdir(TEMPLATE_DIR):
        if not filename.endswith(".html"):
            continue

        filepath = os.path.join(TEMPLATE_DIR, filename)
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
            if regex.search(content):
                found_in.append(filename)

    return found_in

def run_ui_audit():
    print("============================================================")
    print(" 🕵️ UI STRUCTURE & VISIBILITY AUDIT")
    print("============================================================")
    print("Verifying that every backend control has a matching UI element.")

    schemas = [
        ("Browser", BrowserConfigUpdate),
        ("Twilio", TwilioConfigUpdate),
        ("Telnyx", TelnyxConfigUpdate)
    ]

    missing_controls = []
    total_checked = 0
    total_found = 0

    for profile, schema in schemas:
        print(f"\nScanning {profile} Profile Controls...")
        fields = get_schema_fields(schema)

        for alias, name in fields:
            total_checked += 1

            # 1. Try exact match
            found_files = scan_templates_for_binding(alias)

            # 2. If not found, try normalized match (common UI pattern)
            # e.g. 'voicePitch_phone' -> 'voicePitch'
            if not found_files:
                base_alias = alias.replace("_phone", "").replace("_telnyx", "")
                if base_alias != alias:
                    found_files = scan_templates_for_binding(base_alias)

            if not found_files:
                # Some fields might be internally handled or intentionally hidden
                # But we report them for manual verification
                print(f"❌ MISSING UI: {alias} ({name})")
                missing_controls.append(f"{profile}.{alias}")
            else:
                print(f"✅ FOUND: {alias} (via {found_files})")
                total_found += 1

    print("\n============================================================")
    print(" FINAL VERDICT")
    print("============================================================")
    print(f"Controls Checked: {total_checked}")
    print(f"Controls Found:   {total_found}")
    print(f"Missing in UI:    {len(missing_controls)}")

    if missing_controls:
        print("\n⚠️ POTENTIAL UI GAPS:")
        for m in missing_controls:
            print(f" - {m}")
        sys.exit(1)
    else:
        print("\n✅ SUCCESS: All configuration fields have UI bindings.")
        sys.exit(0)

if __name__ == "__main__":
    run_ui_audit()
