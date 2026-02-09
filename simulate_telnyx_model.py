"""
Simulación E2E Completa: Perfil Telnyx - TAB MODEL
Basado en metodología de INFORME_COMPARATIVO_ESTRICTO_10_TABS.md
"""
import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY", "secret123")
BASE_URL = "http://localhost:8000"

print("=" * 100)
print("SIMULACIÓN END-TO-END: PERFIL TELNYX - TAB MODEL")
print("=" * 100)
print()

# Almacenar resultados
results = []

# =============================================================================
# CONTROLES A PROBAR (14 total)
# =============================================================================

test_cases = [
    # LLM Básico (5 controles)
    {
        "id": 1,
        "control": "Proveedor LLM",
        "frontend_key": "provider",
        "test_value": "groq",
        "profile": "telnyx"
    },
    {
        "id": 2,
        "control": "Modelo LLM",
        "frontend_key": "model",
        "test_value": "llama-3.1-70b-versatile",
        "profile": "telnyx"
    },
    {
        "id": 3,
        "control": "Creatividad (Temperature)",
        "frontend_key": "temp",
        "test_value": 0.85,
        "profile": "telnyx"
    },
    {
        "id": 4,
        "control": "Max Tokens",
        "frontend_key": "tokens",
        "test_value": 250,
        "profile": "telnyx"
    },
    {
        "id": 5,
        "control": "System Prompt",
        "frontend_key": "prompt",
        "test_value": "Eres un asistente de ventas profesional para Telnyx. Habla en español de México.",
        "profile": "telnyx"
    },
    
    # LLM Avanzado (6 controles)
    {
        "id": 6,
        "control": "Context Window",
        "frontend_key": "contextWindow",
        "test_value": 12,
        "profile": "telnyx"
    },
    {
        "id": 7,
        "control": "Frequency Penalty",
        "frontend_key": "frequencyPenalty",
        "test_value": 0.6,
        "profile": "telnyx"
    },
    {
        "id": 8,
        "control": "Presence Penalty",
        "frontend_key": "presencePenalty",
        "test_value": 0.4,
        "profile": "telnyx"
    },
    {
        "id": 9,
        "control": "Tool Choice",
        "frontend_key": "toolChoice",
        "test_value": "auto",
        "profile": "telnyx"
    },
    {
        "id": 10,
        "control": "Dynamic Vars Enabled",
        "frontend_key": "dynamicVarsEnabled",
        "test_value": True,
        "profile": "telnyx"
    },
    {
        "id": 11,
        "control": "Dynamic Vars",
        "frontend_key": "dynamicVars",
        "test_value": {"empresa": "Acme Corp", "plan": "Premium"},
        "profile": "telnyx"
    },
    
    # Mensajes & Flujo (3 controles)
    {
        "id": 12,
        "control": "Mensaje Inicial",
        "frontend_key": "msg",
        "test_value": "Hola, soy Andrea de soporte Telnyx. ¿En qué puedo ayudarte?",
        "profile": "telnyx"
    },
    {
        "id": 13,
        "control": "Modo Inicio",
        "frontend_key": "mode",
        "test_value": "speak-first",
        "profile": "telnyx"
    },
    {
        "id": 14,
        "control": "Mensaje Idle",
        "frontend_key": "idleMessage",
        "test_value": "¿Sigues ahí? ¿Necesitas más ayuda?",
        "profile": "telnyx"
    },
]

# =============================================================================
# EJECUTAR PRUEBAS
# =============================================================================

for test in test_cases:
    print(f"\n{'='*100}")
    print(f"TEST #{test['id']}: {test['control']}")
    print(f"{'='*100}")
    
    result = {
        "id": test["id"],
        "control": test["control"],
        "frontend_key": test["frontend_key"],
        "test_value": test["test_value"],
        "http_status": None,
        "http_updated": None,
        "db_persisted": None,
        "readback_value": None,
        "readback_ok": None,
        "errors": [],
        "status": None
    }
    
    # FASE 1: Enviar cambio al API
    print(f"\n📤 FASE 1: Enviando cambio...")
    print(f"   Payload: {{{test['frontend_key']}: {test['test_value']}}}")
    print(f"   Profile: {test['profile']}")
    
    try:
        payload = {test["frontend_key"]: test["test_value"]}
        response = requests.post(
            f"{BASE_URL}/api/config/update-json?profile={test['profile']}",
            json=payload,
            headers={"X-API-Key": API_KEY},
            timeout=5
        )
        
        result["http_status"] = response.status_code
        
        if response.status_code == 200:
            resp_data = response.json()
            result["http_updated"] = resp_data.get("updated", 0)
            print(f"   ✅ HTTP 200 OK")
            print(f"   ✅ Updated: {resp_data.get('updated', 0)} campo(s)")
            print(f"   ✅ Normalized: {resp_data.get('normalized', 0)} campo(s)")
            
            if resp_data.get("warnings"):
                print(f"   ⚠️ Warnings: {resp_data['warnings']}")
                result["errors"].append(f"Warnings: {resp_data['warnings']}")
        else:
            print(f"   ❌ HTTP {response.status_code}")
            print(f"   Error: {response.text}")
            result["errors"].append(f"HTTP {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
        result["errors"].append(f"HTTP Exception: {str(e)}")
    
    # FASE 2: Verificar Readback
    print(f"\n🔍 FASE 2: Verificando Readback...")
    
    try:
        get_response = requests.get(
            f"{BASE_URL}/api/config?profile={test['profile']}",
            headers={"X-API-Key": API_KEY},
            timeout=5
        )
        
        if get_response.status_code == 200:
            config_data = get_response.json()
            
            # Buscar el valor en la respuesta
            readback_value = config_data.get(test["frontend_key"])
            result["readback_value"] = readback_value
            
            # Comparar
            if readback_value == test["test_value"]:
                result["readback_ok"] = True
                print(f"   ✅ Readback OK: {readback_value} == {test['test_value']}")
            else:
                result["readback_ok"] = False
                print(f"   ❌ Readback FAIL: {readback_value} != {test['test_value']}")
                result["errors"].append(f"Readback mismatch: expected {test['test_value']}, got {readback_value}")
        else:
            print(f"   ❌ GET failed: {get_response.status_code}")
            result["errors"].append(f"GET failed: {get_response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
        result["errors"].append(f"Readback Exception: {str(e)}")
    
    # FASE 3: Determinar Status Final
    if (result["http_status"] == 200 and 
        result["http_updated"] and result["http_updated"] > 0 and 
        result["readback_ok"]):
        result["status"] = "✅ PASS"
        print(f"\n🎉 Status: ✅ PASS")
    else:
        result["status"] = "❌ FAIL"
        print(f"\n❌ Status: ❌ FAIL")
        if result["errors"]:
            print(f"   Errores: {result['errors']}")
    
    results.append(result)

# =============================================================================
# RESUMEN
# =============================================================================

print(f"\n\n{'='*100}")
print("RESUMEN FINAL")
print(f"{'='*100}\n")

passed = sum(1 for r in results if r["status"] == "✅ PASS")
failed = sum(1 for r in results if r["status"] == "❌ FAIL")

print(f"Total Tests: {len(results)}")
print(f"✅ Passed: {passed}")
print(f"❌ Failed: {failed}")
print(f"Score: {passed}/{len(results)} ({100 * passed / len(results):.1f}%)")
print()

# Tabla resumida
print("| # | Control | Test Value | HTTP | Readback | Status |")
print("|---|---------|------------|------|----------|--------|")
for r in results:
    tv_str = str(r["test_value"])[:30]
    http_icon = "✅" if r["http_status"] == 200 else "❌"
    rb_icon = "✅" if r["readback_ok"] else "❌"
    print(f"| {r['id']} | {r['control'][:20]} | {tv_str} | {http_icon} {r['http_status']} | {rb_icon} | {r['status']} |")

print()

# Guardar resultados en JSON
with open("telnyx_model_simulation_results.json", "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\n✅ Resultados guardados en: telnyx_model_simulation_results.json")
print(f"{'='*100}\n")
