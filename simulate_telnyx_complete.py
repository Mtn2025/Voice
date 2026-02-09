"""
Simulación E2E COMPLETA - Telnyx MODEL Tab
Con captura detallada de cada POST
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY", "secret123")
BASE_URL = "http://localhost:8000"

print("=" * 100)
print("SIMULACIÓN COMPLETA TELNYX MODEL TAB - CON DIAGNOSTICOS")
print("=" * 100)
print()

# Test simple con mejor diagnóstico
test_cases = [
    {"id": 1, "control": "Proveedor LLM", "key": "provider", "value": "groq"},
    {"id": 2, "control": "Modelo LLM", "key": "model", "value": "llama-3.1-70b-versatile"},
    {"id": 3, "control": "Temperature", "key": "temp", "value": 0.85},
    {"id": 4, "control": "Max Tokens", "key": "tokens", "value": 250},
    {"id": 5, "control": "System Prompt", "key": "prompt", "value": "Eres Andrea, asistente de Telnyx"},
    {"id": 6, "control": "Context Window", "key": "contextWindow", "value": 12},
    {"id": 7, "control": "Frequency Penalty", "key": "frequencyPenalty", "value": 0.6},
    {"id": 8, "control": "Presence Penalty", "key": "presencePenalty", "value": 0.4},
    {"id": 9, "control": "Tool Choice", "key": "toolChoice", "value": "auto"},
    {"id": 10, "control": "Dynamic Vars Enabled", "key": "dynamicVarsEnabled", "value": True},
    {"id": 11, "control": "Dynamic Vars", "key": "dynamicVars", "value": {"empresa": "Test"}},
    {"id": 12, "control": "Mensaje Inicial", "key": "msg", "value": "Hola desde test"},
    {"id": 13, "control": "Modo Inicio", "key": "mode", "value": "speak-first"},
    {"id": 14, "control": "Mensaje Idle", "key": "idleMessage", "value": "¿Sigues ahí?"},
]

results = []

for test in test_cases:
    print(f"\n{'='*100}")
    print(f"TEST #{test['id']}: {test['control']} (key: {test['key']})")
    print(f"{'='*100}")
    
    result = {
        "id": test["id"],
        "control": test["control"],
        "key": test["key"],
        "test_value": test["value"],
        "http_ok": False,
        "readback_ok": False,
        "status": "❌ FAIL"
    }
    
    # POST
    print(f"\n📤POST {{{test['key']}: {test['value']}}}")
    try:
        resp = requests.post(
            f"{BASE_URL}/api/config/update-json?profile=telnyx",
            json={test["key"]: test["value"]},
            headers={"X-API-Key": API_KEY},
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ HTTP 200 - Updated: {data.get('updated')}")
            result["http_ok"] = True
        else:
            print(f"   ❌ HTTP {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # GET
    print(f"\n🔍 GET readback...")
    try:
        resp = requests.get(
            f"{BASE_URL}/api/config?profile=telnyx",
            headers={"X-API-Key": API_KEY},
            timeout=5
        )
        if resp.status_code == 200:
            config = resp.json()
            readback_value = config.get(test["key"])
            
            if readback_value == test["value"]:
                print(f"   ✅ MATCH: {readback_value}")
                result["readback_ok"] = True
                result["status"] = "✅ PASS"
            else:
                print(f"   ❌ MISMATCH: Expected {test['value']}, got {readback_value}")
        else:
            print(f"   ❌ GET failed {resp.status_code}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    results.append(result)

print(f"\n\n{'='*100}")
print("RESUMEN FINAL")
print(f"{'='*100}\n")

passed = sum(1 for r in results if r["status"] == "✅ PASS")
failed = sum(1 for r in results if r["status"] == "❌ FAIL")

print(f"Total: {len(results)}")
print(f"✅ PASS: {passed}")
print(f"❌ FAIL: {failed}")
print(f"Score: {passed}/{len(results)} ({100 * passed / len(results):.1f}%)")
print()

print("| # | Control | Key | Test Value | HTTP | Readback | Status |")
print("|---|---------|-----|------------|------|----------|--------|")
for r in results:
    http_icon = "✅" if r["http_ok"] else "❌"
    rb_icon = "✅" if r["readback_ok"] else "❌"
    val_str = str(r["test_value"])[:20]
    print(f"| {r['id']} | {r['control'][:20]} | {r['key']} | {val_str} | {http_icon} | {rb_icon} | {r['status']} |")

print(f"\n{'='*100}\n")
