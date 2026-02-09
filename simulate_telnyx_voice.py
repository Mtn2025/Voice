"""
SIMULACIÓN COMPLETA E2E: TAB VOICE - PERFIL TELNYX
Metodología: Igual que MODEL tab (POST + GET readback verification)
Total controles: 18
"""

import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY", "secret123")
BASE_URL = "http://localhost:8000"

# Test cases para cada control del tab VOICE
test_cases = [
    # Básicos TTS
    {"id": 1, "control": "Proveedor TTS", "key": "voiceProvider", "value": "azure", "db_column": "tts_provider_telnyx"},
    {"id": 2, "control": "Idioma Voz", "key": "voiceLang", "value": "es-ES", "db_column": "voice_language_telnyx"},
    {"id": 3, "control": "Voz ID", "key": "voiceId", "value": "es-ES-ElviraNeural", "db_column": "voice_name_telnyx"},
    {"id": 4, "control": "Estilo Voz", "key": "voiceStyle", "value": "cheerful", "db_column": "voice_style_telnyx"},
    
    # Expresión de Voz
    {"id": 5, "control": "Velocidad", "key": "voiceSpeed", "value": 1.3, "db_column": "voice_speed_telnyx"},
    {"id": 6, "control": "Tono/Pitch", "key": "voicePitch", "value": 5, "db_column": "voice_pitch_telnyx"},
    {"id": 7, "control": "Volumen", "key": "voiceVolume", "value": 90, "db_column": "voice_volume_telnyx"},
    {"id": 8, "control": "Grado Estilo", "key": "voiceStyleDegree", "value": 1.5, "db_column": "voice_style_degree_telnyx"},
    {"id": 9, "control": "Pausa/Pacing", "key": "voicePacing", "value": 100, "db_column": "voice_pacing_ms_telnyx"},
    
    # Background Audio
    {"id": 10, "control": "Sonido Fondo", "key": "voiceBgSound", "value": "office", "db_column": "background_sound_telnyx"},
    {"id": 11, "control": "URL Audio Fondo", "key": "voiceBgUrl", "value": "https://test.com/audio.mp3", "db_column": "background_sound_url_telnyx"},
    
    # ElevenLabs Avanzado (aunque proveedor es Azure, estos campos deben guardarse)
    {"id": 12, "control": "Estabilidad", "key": "voiceStability", "value": 0.75, "db_column": "voice_stability_telnyx"},
    {"id": 13, "control": "Similitud", "key": "voiceSimilarityBoost", "value": 0.8, "db_column": "voice_similarity_boost_telnyx"},
    {"id": 14, "control": "Exageración Estilo", "key": "voiceStyleExaggeration", "value": 0.6, "db_column": "voice_style_exaggeration_telnyx"},
    {"id": 15, "control": "Speaker Boost", "key": "voiceSpeakerBoost", "value": True, "db_column": "voice_speaker_boost_telnyx"},
    {"id": 16, "control": "Multilingüe", "key": "voiceMultilingual", "value": False, "db_column": "voice_multilingual_telnyx"},
    
    # Humanización
    {"id": 17, "control": "Filler Injection", "key": "voiceFillerInjection", "value": True, "db_column": "voice_filler_injection_telnyx"},
    {"id": 18, "control": "Backchannel", "key": "voiceBackchanneling", "value": True, "db_column": "voice_backchanneling_telnyx"},
    
    # Técnicos
    {"id": 19, "control": "Latency Optimization", "key": "ttsLatencyOptimization", "value": 1, "db_column": "tts_latency_optimization_telnyx"},
    {"id": 20, "control": "Output Format", "key": "ttsOutputFormat", "value": "pcm_16000", "db_column": "tts_output_format_telnyx"},
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
        
        # Comparación
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
    print("SIMULACIÓN COMPLETA TELNYX VOICE TAB - CON DIAGNOSTICOS")
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
