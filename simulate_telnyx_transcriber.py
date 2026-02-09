"""
SIMULACIÓN COMPLETA E2E: TAB TRANSCRIBER - PERFIL TELNYX
Metodología: Igual que MODEL y VOICE tabs
Total controles: 11
"""

import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY", "secret123")
BASE_URL = "http://localhost:8000"

# Test cases para tab TRANSCRIBER
test_cases = [
    # Básicos STT
    {"id": 1, "control": "Proveedor STT", "key": "sttProvider", "value": "deepgram", "db_column": "stt_provider_telnyx"},
    {"id": 2, "control": "Idioma STT", "key": "sttLang", "value": "es", "db_column": "stt_language_telnyx"},
    {"id": 3, "control": "Modelo STT", "key": "sttModel", "value": "nova-2", "db_column": "stt_model_telnyx"},
    
    # Keywords & Timing
    {"id": 4, "control": "Keywords Boosting", "key": "sttKeywords", "value": '[{"word": "Ubrokers", "boost": 2.0}]', "db_column": "stt_keywords_telnyx"},
    {"id": 5, "control": "Silence Timeout", "key": "sttSilenceTimeout", "value": 800, "db_column": "stt_silence_timeout_telnyx"},
   
    # VAD & Intelligent Interruption
    {"id": 6, "control": "Utterance End Mode", "key": "sttUtteranceEnd", "value": "semantic", "db_column": "stt_utterance_end_telnyx"},
    {"id": 7, "control": "VAD Threshold", "key": "vadThreshold", "value": 0.6, "db_column": "vad_threshold_telnyx"},
    
    # Inteligencia de Transcripción
    {"id": 8, "control": "Punctuation", "key": "sttPunctuation", "value": True, "db_column": "stt_punctuation_telnyx"},
    {"id": 9, "control": "Smart Formatting", "key": "sttSmartFormatting", "value": True, "db_column": "stt_smart_formatting_telnyx"},
    {"id": 10, "control": "Profanity Filter", "key": "sttProfanityFilter", "value": False, "db_column": "stt_profanity_filter_telnyx"},
    {"id": 11, "control": "Diarization", "key": "sttDiarization", "value": True, "db_column": "stt_diarization_telnyx"},
]

def run_test(test):
    """Ejecuta un test: POST + GET readback + verificación"""
    print(f"\n{'='*100}")
    print(f"TEST #{test['id']}: {test['control']} (key: {test['key']})")
    print(f"{'='*100}\n")
    
    # POST
    print(f"📤POST {{{test['key']}: {test['value']}}}")
    try:
        resp = requests.post(
            f"{BASE_URL}/api/config/update-json?profile=telnyx",
            json={test['key']: test['value']},
            headers={"X-API-Key": API_KEY},
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ HTTP {resp.status_code} - Updated: {data.get('updated', 0)}")
        else:
            print(f"   ❌ HTTP {resp.status_code}")
            return {"test": test, "post_status": resp.status_code, "get_status": None, "match": False, "error": f"POST failed: {resp.status_code}"}
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return {"test": test, "post_status": None, "get_status": None, "match": False, "error": str(e)}
    
    # GET readback
    print(f"\n🔍 GET readback...")
    try:
        resp = requests.get(
            f"{BASE_URL}/api/config?profile=telnyx",
            headers={"X-API-Key": API_KEY},
            timeout=10
        )
        
        if resp.status_code != 200:
            print(f"   ❌ HTTP {resp.status_code}")
            return {"test": test, "post_status": 200, "get_status": resp.status_code, "match": False, "error": f"GET failed: {resp.status_code}"}
        
        config = resp.json()
        actual_value = config.get(test['key'])
        expected_value = test['value']
        
        # Para JSON strings, comparar como objetos
        if isinstance(expected_value, str) and expected_value.startswith('['):
            try:
                expected_obj = json.loads(expected_value)
                # API puede devolver dict o string - ambos son válidos
                if isinstance(actual_value, str):
                    actual_obj = json.loads(actual_value)
                    if actual_obj == expected_obj:
                        print(f"   ✅ MATCH: {actual_value}")
                        return {"test": test, "post_status": 200, "get_status": 200, "match": True, "actual": actual_value}
                elif actual_value == expected_obj:
                    print(f"   ✅ MATCH: {actual_value}")
                    return {"test": test, "post_status": 200, "get_status": 200, "match": True, "actual": actual_value}
                else:
                    print(f"   ❌ MISMATCH: Expected {expected_obj}, got {actual_value}")
                    return {"test": test, "post_status": 200, "get_status": 200, "match": False, "actual": actual_value, "expected": expected_obj}
            except:
                pass
        
        # Comparación normal
        if actual_value == expected_value:
            print(f"   ✅ MATCH: {actual_value}")
            return {"test": test, "post_status": 200, "get_status": 200, "match": True, "actual": actual_value}
        else:
            print(f"   ❌ MISMATCH: Expected {expected_value}, got {actual_value}")
            return {"test": test, "post_status": 200, "get_status": 200, "match": False, "actual": actual_value, "expected": expected_value}
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return {"test": test, "post_status": 200, "get_status": None, "match": False, "error": str(e)}


def main():
    print("="*100)
    print("SIMULACIÓN COMPLETA TELNYX TRANSCRIBER TAB - CON DIAGNOSTICOS")
    print("="*100)
    print("\n")
    
    results = []
    for test in test_cases:
        result = run_test(test)
        results.append(result)
    
    # Resumen final
    print("\n")
    print("="*100)
    print("RESUMEN FINAL")
    print("="*100)
    print()
    
    total = len(results)
    passed = sum(1 for r in results if r["match"])
    failed = total - passed
    
    print(f"Total: {total}")
    print(f"✅ PASS: {passed}")
    print(f"❌ FAIL: {failed}")
    print(f"Score: {passed}/{total} ({passed/total*100:.1f}%)")
    print()
    
    # Tabla
    print("| # | Control | Key | Test Value | HTTP | Readback | Status |")
    print("|---|---------|-----|------------|------|----------|--------|")
    
    for r in results:
        test = r["test"]
        value_str = str(test["value"])[:20]
        http_status = "✅" if r["post_status"] == 200 else "❌"
        readback_status = "✅" if r["get_status"] == 200 else "❌"
        final_status = "✅ PASS" if r["match"] else "❌ FAIL"
        
        print(f"| {test['id']} | {test['control']} | {test['key']} | {value_str} | {http_status} | {readback_status} | {final_status} |")
    
    print()
    print("="*100)


if __name__ == "__main__":
    main()
