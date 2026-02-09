"""
E2E Simulation: Telnyx REMAINING TABS (CONNECTIVITY + SYSTEM + ADVANCED + FLOW + ANALYSIS)
Tests representative Telnyx-specific controls for complete audit
"""
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("ADMIN_API_KEY")
HEADERS = {"X-API-Key": API_KEY}

# Selected representative controls from remaining tabs (Telnyx-specific _telnyx suffix fields)
TEST_CASES = [
    # CONNECTIVITY Tab (2 controls)
    {"id": 1, "tab": "CONNECTIVITY", "control": "Telnyx Connection ID", "key": "telnyxConnectionId", "value": "conn_12345abc", "db_column": "telnyx_connection_id_telnyx"},
    {"id": 2, "tab": "CONNECTIVITY", "control": "Caller ID Override", "key": "callerIdTelnyx", "value": "+19175551234", "db_column": "caller_id_telnyx"},
    
    # SYSTEM Tab (5 controls - Profile-agnostic, not Telnyx-specific)
    # NOTE: These don't have _telnyx suffix, so they apply to ALL profiles
    {"id": 3, "tab": "SYSTEM", "control": "Concurrency Limit", "key": "concurrencyLimit", "value": 25, "db_column": "concurrency_limit"},
    {"id": 4, "tab": "SYSTEM", "control": "Spend Limit Daily", "key": "spendLimitDaily", "value": 100.50, "db_column": "spend_limit_daily"},
    {"id": 5, "tab": "SYSTEM", "control": "Environment", "key": "environment", "value": "production", "db_column": "environment"},
    {"id": 6, "tab": "SYSTEM", "control": "Privacy Mode", "key": "privacyMode", "value": True, "db_column": "privacy_mode"},
    {"id": 7, "tab": "SYSTEM", "control": "Audit Log Enabled", "key": "auditLogEnabled", "value": True, "db_column": "audit_log_enabled"},
    
    # ADVANCED Tab (3 controls - Telnyx-specific)
    {"id": 8, "tab": "ADVANCED", "control": "Noise Suppression Level", "key": "noiseSuppressionLevel", "value": "balanced", "db_column": "noise_suppression_level_telnyx"},
    {"id": 9, "tab": "ADVANCED", "control": "Audio Codec", "key": "audioCodec", "value": "OPUS", "db_column": "audio_codec_telnyx"},
    {"id": 10, "tab": "ADVANCED", "control": "Enable Backchannel", "key": "enableBackchannel", "value": True, "db_column": "enable_backchannel_telnyx"},
    
    # FLOW Tab (3 representative controls - Profile-agnostic)
    {"id": 11, "tab": "FLOW", "control": "Barge-In Enabled", "key": "bargeInEnabled", "value": True, "db_column": "barge_in_enabled"},
    {"id": 12, "tab": "FLOW", "control": "Interruption Sensitivity", "key": "interruptionSensitivity", "value": 0.7, "db_column": "interruption_sensitivity"},
    {"id": 13, "tab": "FLOW", "control": "Voicemail Detection", "key": "voicemailDetectionEnabled", "value": True, "db_column": "voicemail_detection_enabled"},
    
    # ANALYSIS Tab (4 controls)
    {"id": 14, "tab": "ANALYSIS", "control": "Analysis Prompt", "key": "analysisPrompt", "value": "Resume en 3 bullets", "db_column": "analysis_prompt"},
    {"id": 15, "tab": "ANALYSIS", "control": "Success Rubric", "key": "successRubric", "value": "Cliente aceptó cita", "db_column": "success_rubric"},
    {"id": 16, "tab": "ANALYSIS", "control": "Sentiment Analysis", "key": "sentimentAnalysis", "value": True, "db_column": "sentiment_analysis"},
    {"id": 17, "tab": "ANALYSIS", "control": "Cost Tracking", "key": "costTrackingEnabled", "value": True, "db_column": "cost_tracking_enabled"},
]

def run_test(test):
    """Run a single E2E test"""
    print("=" * 100)
    print(f"TEST #{test['id']}: [{test['tab']}] {test['control']} (key:{test['key']})")
    print("=" * 100)
    
    # POST
    payload = {test['key']: test['value']}
    print(f"\n📤POST {payload}")
    
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
                print(f"   ⚠️  WARNING: Updated=0 (field may not exist in Telnyx profile or wrong alias)")
        else:
            print(f"   ❌ HTTP {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ POST failed: {e}")
        return False
    
    # GET readback
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
        
        # Compare (flexible type comparison for numbers)
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
            print(f"      Got: {actual_value} ({type(actual_value).__name__})")
            return False
    except Exception as e:
        print(f"   ❌ GET failed: {e}")
        return False

def main():
    print("=" * 100)
    print("SIMULACIÓN CONSOLIDADA: TABS RESTANTES (CONNECTIVITY + SYSTEM + ADVANCED + FLOW + ANALYSIS)")
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
            "value": test['value'],
            "passed": passed
        })
        print("\n")
    
    # Summary by tab
    print("=" * 100)
    print("RESUMEN POR TAB")
    print("=" * 100)
    
    tabs = {}
    for r in results:
        tab_name = r['tab']
        if tab_name not in tabs:
            tabs[tab_name] = {"passed": 0, "total": 0}
        tabs[tab_name]['total'] += 1
        if r['passed']:
            tabs[tab_name]['passed'] += 1
    
    for tab_name, stats in tabs.items():
        pct = 100 * stats['passed'] / stats['total'] if stats['total'] > 0 else 0
        status = "✅" if stats['passed'] == stats['total'] else "⚠️"
        print(f"{status} {tab_name}: {stats['passed']}/{stats['total']} ({pct:.1f}%)")
    
    # Overall summary
    print("\n" + "=" * 100)
    print("RESUMEN GENERAL")
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

if __name__ == "__main__":
    main()
