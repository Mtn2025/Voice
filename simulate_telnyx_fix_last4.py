"""
E2E Simulation: Fixing Last 4 Telnyx Controls with Correct Schema Aliases
"""
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("ADMIN_API_KEY")
HEADERS = {"X-API-Key": API_KEY}

# Using CORRECT aliases from Pydantic schema
TEST_CASES = [
    {"id": 1, "control": "Telnyx Connection ID", "key": "telnyxConnectionId", "value": "conn_TEST_67890", "schema_alias": "telnyxConnectionId"},
    {"id": 2, "control": "Caller ID Telnyx", "key": "callerIdTelnyx", "value": "+19175559999", "schema_alias": "callerIdTelnyx"},
    {"id": 3, "control": "Daily Spend Limit", "key": "dailySpendLimit", "value": 150.75, "schema_alias": "dailySpendLimit"},
    {"id": 4, "control": "Environment Tag", "key": "environmentTag", "value": "staging", "schema_alias": "environmentTag"},
]

def run_test(test):
    """Run a single E2E test with correct alias"""
    print("=" * 100)
    print(f"TEST #{test['id']}: {test['control']} (key:{test['key']})")
    print("=" * 100)
    
    # POST
    payload = {test['key']: test['value']}
    print(f"\n📤 POST {payload}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/config/update-json?profile=telnyx",
            json=payload,
            headers=HEADERS
        )
        
        if response.status_code == 200:
            result = response.json()
            updated = result.get('updated', 0)
            print(f"   ✅ HTTP 200 - Updated: {updated}")
            if updated == 0:
                print(f"   ⚠️  WARNING: Updated=0 (field may not persist)")
        else:
            print(f"   ❌ HTTP {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ POST failed: {e}")
        return False
    
    # GET readback using SCHEMA ALIAS
    print(f"\n🔍 GET readback with alias '{test['schema_alias']}'...")
    try:
        get_response = requests.get(
            f"{BASE_URL}/api/config?profile=telnyx",
            headers=HEADERS
        )
        
        if get_response.status_code != 200:
            print(f"   ❌ GET failed: {get_response.status_code}")
            return False
        
        config = get_response.json()
        actual_value = config.get(test['schema_alias'])
        
        # Compare
        expected = test['value']
        if isinstance(expected, float) and isinstance(actual_value, (int, float)):
            match = abs(float(actual_value) - expected) < 0.01
        elif isinstance(expected, int) and isinstance(actual_value, (int, float)):
            match = int(actual_value) == expected
        else:
            match = actual_value == expected
        
        if match:
            print(f"   ✅ MATCH: {actual_value}")
            return True
        else:
            print(f"   ❌ MISMATCH")
            print(f"      Expected: {expected} ({type(expected).__name__})")
            print(f"      Got: {actual_value} ({type(actual_value).__name__ if actual_value is not None else 'NoneType'})")
            return False
    except Exception as e:
        print(f"   ❌ GET failed: {e}")
        return False

def main():
    print("=" * 100)
    print("FIXING LAST 4 TELNYX CONTROLS - Using Correct Schema Aliases")
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
    
    print(f"\nTotal Tested: {total}")
    print(f"✅ PASS: {passed_count}")
    print(f"❌ FAIL: {total - passed_count}")
    print(f"Score: {passed_count}/{total} ({100*passed_count/total:.1f}%)")
    
    # Table
    print(f"\n| # | Control | Key | Status |")
    print(f"|---|---------|-----|--------|")
    for r in results:
        status = "✅ PASS" if r['passed'] else "❌ FAIL"
        print(f"| {r['id']} | {r['control']} | {r['key']} | {status} |")
    
    print("\n" + "=" * 100)
    
    if passed_count == total:
        print("🎉 ¡TODOS LOS CONTROLES RESTANTES PASARON!")
    else:
        print(f"⚠️  Quedan {total - passed_count} controles con problemas")

if __name__ == "__main__":
    main()
