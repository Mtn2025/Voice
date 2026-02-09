"""
E2E Simulation: Telnyx TOOLS Tab
Tests all 11 controls for proper POST → DB → GET flow
"""
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("ADMIN_API_KEY")
HEADERS = {"X-API-Key": API_KEY}

# Test cases for TOOLS tab (11 controls)
TEST_CASES = [
    # Schema Sub-tab
    {"id": 1, "control": "Tools Schema", "key": "toolsSchema", "value": [{"type": "function", "function": {"name": "test_tool"}}], "db_column": "tools_schema_telnyx"},
    {"id": 2, "control": "Async Tools", "key": "asyncTools", "value": True, "db_column": "async_tools_telnyx"},
    
    # Server Sub-tab
    {"id": 3, "control": "Tool Server URL", "key": "toolServerUrl", "value": "https://n8n.example.com/webhook/test", "db_column": "tool_server_url_telnyx"},
    {"id": 4, "control": "Tool Server Secret", "key": "toolServerSecret", "value": "Bearer sk-test123", "db_column": "tool_server_secret_telnyx"},
    {"id": 5, "control": "Tool Timeout", "key": "toolTimeoutMs", "value": 8000, "db_column": "tool_timeout_ms_telnyx"},
    {"id": 6, "control": "Tool Retry Count", "key": "toolRetryCount", "value": 1, "db_column": "tool_retry_count_telnyx"},
    {"id": 7, "control": "Tool Error Message", "key": "toolErrorMsg", "value": "Error personalizado de prueba", "db_column": "tool_error_msg_telnyx"},
    {"id": 8, "control": "Client Tools Enabled", "key": "clientToolsEnabled", "value": True, "db_column": "client_tools_enabled_telnyx"},
    
    # Security Sub-tab
    {"id": 9, "control": "Redact Params", "key": "redactParams", "value": ["password", "credit_card"], "db_column": "redact_params_telnyx"},
    {"id": 10, "control": "Transfer Whitelist", "key": "transferWhitelist", "value": ["+15550001", "+15550002"], "db_column": "transfer_whitelist_telnyx"},
    {"id": 11, "control": "State Injection Enabled", "key": "stateInjectionEnabled", "value": False, "db_column": "state_injection_enabled_telnyx"},
]

def json_equals(a, b):
    """Compare two values, handling JSON strings vs dicts"""
    # If both are dicts/lists, compare directly
    if isinstance(a, (dict, list)) and isinstance(b, (dict, list)):
        return a == b
    # If one is string and other is dict/list, parse and compare
    if isinstance(a, str) and isinstance(b, (dict, list)):
        try:
            return json.loads(a) == b
        except:
            return False
    if isinstance(b, str) and isinstance(a, (dict, list)):
        try:
            return a == json.loads(b)
        except:
            return False
    # Direct comparison
    return a == b

def run_test(test):
    """Run a single E2E test"""
    print("=" * 100)
    print(f"TEST #{test['id']}: {test['control']} (key: {test['key']})")
    print("=" * 100)
    
    # POST
    payload = {test['key']: test['value']}
    print(f"\n📤POST {payload}")
    
    response = requests.post(
        f"{BASE_URL}/api/config/update-json?profile=telnyx",
        json=payload,
        headers=HEADERS
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ HTTP 200 - Updated: {result.get('updated', 0)}")
    else:
        print(f"   ❌ HTTP {response.status_code}")
        return False
    
    # GET readback
    print(f"\n🔍 GET readback...")
    get_response = requests.get(
        f"{BASE_URL}/api/config?profile=telnyx",
        headers=HEADERS
    )
    
    if get_response.status_code != 200:
        print(f"   ❌ GET failed: {get_response.status_code}")
        return False
    
    config = get_response.json()
    actual_value = config.get(test['key'])
    
    # Compare
    if json_equals(actual_value, test['value']):
        print(f"   ✅ MATCH: {actual_value}")
        return True
    else:
        print(f"   ❌ MISMATCH")
        print(f"      Expected: {test['value']}")
        print(f"      Got: {actual_value}")
        return False

def main():
    print("=" * 100)
    print("SIMULACIÓN COMPLETA TELNYX TOOLS TAB - CON DIAGNOSTICOS")
    print("=" * 100)
    print("\n\n")
    
    results = []
    for test in TEST_CASES:
        passed = run_test(test)
        results.append({
            "id": test['id'],
            "control": test['control'],
            "key": test['key'],
            "value": str(test['value'])[:20] if isinstance(test['value'], (dict, list)) else test['value'],
            "passed": passed
        })
        print("\n")
    
    # Summary
    print("=" * 100)
    print("RESUMEN FINAL")
    print("=" * 100)
    
    passed_count = sum(1 for r in results if r['passed'])
    total = len(results)
    
    print(f"\nTotal: {total}")
    print(f"✅ PASS: {passed_count}")
    print(f"❌ FAIL: {total - passed_count}")
    print(f"Score: {passed_count}/{total} ({100*passed_count/total:.1f}%)")
    
    # Table
    print(f"\n| # | Control | Key | Test Value | HTTP | Readback | Status |")
    print(f"|---|---------|-----|------------|------|----------|--------|")
    for r in results:
        status = "✅ PASS" if r['passed'] else "❌ FAIL"
        http_mark = "✅" if r['passed'] else "❌"
        readback_mark = "✅" if r['passed'] else "❌"
        print(f"| {r['id']} | {r['control']} | {r['key']} | {r['value']} | {http_mark} | {readback_mark} | {status} |")
    
    print("\n" + "=" * 100)

if __name__ == "__main__":
    main()
