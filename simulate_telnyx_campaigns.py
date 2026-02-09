"""
E2E Simulation: Telnyx CAMPAIGNS Tab
Tests all 3 integration controls for proper POST → DB → GET flow
"""
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("ADMIN_API_KEY")
HEADERS = {"X-API-Key": API_KEY}

# Test cases for CAMPAIGNS tab (3 controls - Integrations)
TEST_CASES = [
    {"id": 1, "control": "CRM Enabled", "key": "crmEnabled", "value": True, "db_column": "crm_enabled_telnyx"},
    {"id": 2, "control": "Webhook URL", "key": "webhookUrl", "value": "https://webhook.site/test-telnyx", "db_column": "webhook_url_telnyx"},
    {"id": 3, "control": "Webhook Secret", "key": "webhookSecret", "value": "secret_test_12345", "db_column": "webhook_secret_telnyx"},
]

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
    if actual_value == test['value']:
        print(f"   ✅ MATCH: {actual_value}")
        return True
    else:
        print(f"   ❌ MISMATCH")
        print(f"      Expected: {test['value']}")
        print(f"      Got: {actual_value}")
        return False

def main():
    print("=" * 100)
    print("SIMULACIÓN COMPLETA TELNYX CAMPAIGNS TAB - INTEGRATIONS")
    print("=" * 100)
    print("\n\n")
    
    results = []
    for test in TEST_CASES:
        passed = run_test(test)
        results.append({
            "id": test['id'],
            "control": test['control'],
            "key": test['key'],
            "value": test['value'],
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
        value_display = str(r['value'])[:30]
        print(f"| {r['id']} | {r['control']} | {r['key']} | {value_display} | {http_mark} | {readback_mark} | {status} |")
    
    print("\n" + "=" * 100)

if __name__ == "__main__":
    main()
