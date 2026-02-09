"""Test individual: System Prompt"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY", "secret123")
BASE_URL = "http://localhost:8000"

print("="*80)
print("TEST: System Prompt (prompt → system_prompt_telnyx)")
print("="*80)
print()

# 1. Ver valor actual
print("1. GET valor actual...")
resp = requests.get(f"{BASE_URL}/api/config?profile=telnyx", headers={"X-API-Key": API_KEY})
current = resp.json().get("prompt")
print(f"   Actual: {current}")
print()

# 2. Enviar nuevo valor
new_value = "PRUEBA DE SISTEMA PROMPT MODIFICADO"
print(f"2. POST nuevo valor: '{new_value}'...")
resp = requests.post(
    f"{BASE_URL}/api/config/update-json?profile=telnyx",
    json={"prompt": new_value},
    headers={"X-API-Key": API_KEY}
)
print(f"   HTTP {resp.status_code}")
print(f"   Response: {resp.json()}")
print()

# 3. Readback
print("3. GET para verificar...")
resp = requests.get(f"{BASE_URL}/api/config?profile=telnyx", headers={"X-API-Key": API_KEY})
readback = resp.json().get("prompt")
print(f"   Readback: {readback}")
print()

# 4. Comparar
if readback == new_value:
    print("✅ SUCCESS: Valor guardado correctamente")
else:
    print(f"❌ FAIL: Esperado '{new_value}', obtenido '{readback}'")
