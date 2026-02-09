"""
E2E Simulation - FINAL COMPLETE: All 17 Remaining Telnyx Controls
Uusing CORRECT schema aliases for 100% pass rate
"""
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("ADMIN_API_KEY")
HEADERS = {"X-API-Key": API_KEY}

# ALL 17 controls with CORRECT aliases matching Pydantic schema
TEST_CASES = [
    # CONNECTIVITY (2 controls) - Using correct aliases
    {"id": 1, "tab": "CONNECTIVITY", "control": "Telnyx Connection ID", "key": "telnyxConnectionId", "value": "conn_FINAL_TEST"},
    {"id": 2, "tab": "CONNECTIVITY", "control": "Caller ID Telnyx", "key": "callerIdTelnyx", "value": "+19175559000"},
    
    # SYSTEM (5 controls) - FIXED: Using dailySpendLimit and environmentTag  
    {"id": 3, "tab": "SYSTEM", "control": "Concurrency Limit", "key": "concurrencyLimit", "value": 30},
    {"id": 4, "tab": "SYSTEM", "control": "Daily Spend Limit", "key": "dailySpendLimit", "value": 200.75},  # FIXED ALIAS
    {"id": 5, "tab": "SYSTEM", "control": "Environment Tag", "key": "environmentTag", "value": "development"},  # FIXED ALIAS
    {"id": 6, "tab": "SYSTEM", "control": "Privacy Mode", "key": "privacyMode", "value": False},
    {"id": 7, "tab": "SYSTEM", "control": "Audit Log Enabled", "key": "auditLogEnabled", "value": False},
    
    # ADVANCED (3 controls)
    {"id": 8, "tab": "ADVANCED", "control": "Noise Suppression", "key": "noiseSuppressionLevel", "value": "high"},
    {"id": 9, "tab": "ADVANCED", "control": "Audio Codec", "key": "audioCodec", "value": "PCMU"},
    {"id": 10, "tab": "ADVANCED", "control": "Enable Backchannel", "key": "enableBackchannel", "value": False},
    
    # FLOW (3 controls)
    {"id": 11, "tab": "FLOW", "control": "Barge-In Enabled", "key": "bargeInEnabled", "value": False},
    {"id": 12, "tab": "FLOW", "control": "Interruption Sensitivity", "key": "interruptionSensitivity", "value": 0.9},
    {"id": 13, "tab": "FLOW", "control": "Voicemail Detection", "key": "voicemailDetectionEnabled", "value": False},
    
    # ANALYSIS (4 controls)
    {"id": 14, "tab": "ANALYSIS", "control": "Analysis Prompt", "key": "analysisPrompt", "value": "Análisis completo"},
    {"id": 15, "tab": "ANALYSIS", "control": "Success Rubric", "key": "successRubric", "value": "Venta cerrada"},
    {"id": 16, "tab": "ANALYSIS", "control": "Sentiment Analysis", "key": "sentimentAnalysis", "value": False},
    {"id": 17, "tab": "ANALYSIS", "control": "Cost Tracking", "key": "costTrackingEnabled", "value": False},
]

def run_test(test):
    """Run single E2E test: POST → DB → GET"""
    print("=" * 100)
    print(f"TEST #{test['id']}: [{test['tab']}] {test['control']} (key:{test['key']})")
    print("=" * 100)
    
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
                print(f"   ⚠️  WARNING: Updated=0")
        else:
            print(f"   ❌ HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ POST failed: {e}")
        return False
    
    print(f"\n🔍 GET readback...")
    try:
        get_response = requests.get(
            f"{BASE_URL}/api/config?profile=telnyx",
            headers=HEADERS
        )
        
        if get_response.status_code != 200:
            print(f"   ❌ GET failed: {get_response.status_code}")
            return False
        
        config = get_response.json()
        actual_value = config.get(test['key'])
        expected = test['value']
        
        # Flexible type comparison
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
            print(f"   ❌ M ISMATCH")
            print(f"      Expected: {expected} ({type(expected).__name__})")
            print(f"      Got: {actual_value} ({type(actual_value).__name__ if actual_value is not None else 'NoneType'})")
            return False
    except Exception as e:
        print(f"   ❌ GET failed: {e}")
        return False

def main():
    print("=" * 100)
    print("🎯 FINAL VALIDATION: ALL 17 REMAINING TELNYX CONTROLS")
    print("=" * 100)
    print("\n\n")
    
    results = []
    for test in TEST_CASES:
        passed = run_test(test)
        results.append({
            "id": test['id'],
            "tab": test['tab'],
            "control": test['control'],
            "key": test['key'],
            "passed": passed
        })
        print("\n")
    
    # Summary by tab
    print("=" * 100)
    print("RESUMEN POR TAB")
    print("=" * 100)
    
    tabs = {}
    for r in results:
        tab = r['tab']
        if tab not in tabs:
            tabs[tab] = {"passed": 0, "total": 0}
        tabs[tab]['total'] += 1
        if r['passed']:
            tabs[tab]['passed'] += 1
    
    for tab_name, stats in tabs.items():
        pct = 100 * stats['passed'] / stats['total'] if stats['total'] > 0 else 0
        status = "✅" if stats['passed'] == stats['total'] else "❌"
        print(f"{status} {tab_name}: {stats['passed']}/{stats['total']} ({pct:.1f}%)")
    
    # Overall summary
    print("\n" + "=" * 100)
    print("RESUMEN GENERAL - VALIDACIÓN FINAL")
    print("=" * 100)
    
    passed_count = sum(1 for r in results if r['passed'])
    total = len(results)
    
    print(f"\nTotal Tested: {total}")
    print(f"✅ PASS: {passed_count}")
    print(f"❌ FAIL: {total - passed_count}")
    print(f"Score: {passed_count}/{total} ({100*passed_count/total:.1f}%)")
    
    # Table
    print(f"\n| # | Tab | Control | Key | Status |")
    print(f"|---|-----|---------|-----|--------|")
    for r in results:
        status = "✅ PASS" if r['passed'] else "❌ FAIL"
        print(f"| {r['id']} | {r['tab']} | {r['control']} | {r['key']} | {status} |")
    
    print("\n" + "=" * 100)
    
    if passed_count == total:
        print("🎉 ¡¡¡100% SUCCESS!!! TODOS LOS CONTROLES FUNCIONANDO")
        print("🏆 PERFIL TELNYX: PRODUCTION READY")
    else:
        print(f"⚠️  {total - passed_count} controles pendientes")

if __name__ == "__main__":
    main()
