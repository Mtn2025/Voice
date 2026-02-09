import asyncio
import requests
import logging
import os
from dotenv import load_dotenv

# Setup
load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY", "secret123")
BASE_URL = "http://localhost:8000"

# Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("GapCloser")

async def update_config(payload):
    url = f"{BASE_URL}/api/config/update-json?context_type=browser"
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, str(e)

async def main():
    print("🚀 Starting GAP CLOSURE Simulation (Model Tab Part 2)...")
    
    # GAP LIST FROM AUDIT REPORT
    gap_test_cases = [
        # A. Conversation Style
        ("responseLength", "detailed", "Longitud Respuesta"),
        ("conversationTone", "empathetic", "Tono Conversación"),
        ("conversationFormality", "casual", "Nivel Formalidad"),
        ("conversationPacing", "relaxed", "Velocidad"),

        # B. Advanced Intelligence
        ("contextWindow", 25, "Ventana Contexto (Int)"),
        ("frequencyPenalty", 1.5, "Frequency Penalty (Float)"),
        ("presencePenalty", 0.5, "Presence Penalty (Float)"),
        ("toolChoice", "required", "Tool Choice Strategy"),
        # Dynamic Vars intentionally simple text for testing string storage if not dict
        # In DB it is JSON, but endpoint might expect stringified or raw.
        # Let's try raw config update which usually handles it.
        
        # C. Safety & Start
        ("first_message", "Hola, prueba de gap.", "Mensaje Inicial"),
        ("first_message_mode", "listen-first", "Modo Inicio"),
        ("blacklist", "Maldicion,Grosera", "Lista Negra"),
    ]

    print(f"{'CONTROL':<30} | {'VALUE':<15} | {'SAVED':<10} | {'RESULT'}")
    print("-" * 80)

    all_passed = True
    for ui_key, value, label in gap_test_cases:
        # Note: Frontend aliases need to be respected.
        # responseLength -> response_length (Handled by aliasing in dashboard.py?)
        # Let's verify dashboard.py aliases quickly...
        # 'responseLength': 'response_length' -> YES
        # 'contextWindow': 'context_window' -> NOT IN ALIAS LIST in previous view?
        # WE MUST CHECK ALIASES. If not in alias list, config update might fail or ignore.
        
        success, info = await update_config({ui_key: value})
        
        status = "❌ FAIL"
        saved = "NO"
        
        if success and isinstance(info, dict) and info.get("updated", 0) > 0:
            status = "✅ PASS"
            saved = "YES"
        elif success:
            status = "⚠️ IGNORED"
            saved = "NO"
            all_passed = False
        else:
            status = f"💥 ERR: {info}"
            all_passed = False
            
        print(f"{label:<30} | {str(value):<15} | {saved:<10} | {status}")

    print("-" * 80)
    if all_passed:
        print("🎉 GAP CLOSED: All previously untested controls are now VERIFIED.")
    else:
        print("⚠️ GAP REMAINS: Some controls were ignored or failed.")

if __name__ == "__main__":
    asyncio.run(main())
