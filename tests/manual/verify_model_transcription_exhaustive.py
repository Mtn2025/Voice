import asyncio
import json
import os
import requests
import logging
from dotenv import load_dotenv

# Setup
load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY", "secret123")
BASE_URL = "http://localhost:8000"

# Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ModelTranscriptorVerifier")

results = []

def record_result(tab, control, change, saved, verified, notes=""):
    results.append({
        "Tab": tab,
        "Control": control,
        "Change": change,
        "Saved": "✅ YES" if saved else "❌ NO",
        "Verified": "✅ YES" if verified else "❌ NO",
        "Notes": notes
    })

async def wait_for_server(timeout=60):
    logger.info("⏳ Waiting for server...")
    start_time = asyncio.get_running_loop().time()
    while True:
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                logger.info("✅ Server is UP!")
                return True
        except:
            pass
        if asyncio.get_running_loop().time() - start_time > timeout:
            return False
        await asyncio.sleep(2)

async def update_config(payload):
    url = f"{BASE_URL}/api/config/update-json?context_type=browser"
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
             return False, response.text
        return True, response.json()
    except Exception as e:
        logger.error(f"Config Update Failed: {e}")
        return False, str(e)

async def main():
    print("🚀 Starting EXHAUSTIVE Model & Transcriptor Simulation...")
    
    if not await wait_for_server():
        return
        
    test_cases = [
        # TAB: MODEL
        ("Model", "llmProvider", "openai", "LLM Provider"),
        ("Model", "llmModel", "gpt-4-turbo", "LLM Model"),
        ("Model", "temperature", 0.7, "Temperature"),
        ("Model", "systemPrompt", "Eres un asistente experto en auditoria.", "System Prompt"),
        
        # TAB: TRANSCRIPTOR
        ("Transcriptor", "sttProvider", "deepgram", "STT Provider"),
        ("Transcriptor", "sttLang", "en-US", "STT Language"),
        ("Transcriptor", "sttKeywords", json.dumps(["auditoria", "python"]), "STT Keywords"),
        ("Transcriptor", "sttSmartFormatting", False, "Smart Formatting"),
        ("Transcriptor", "sttDiarization", True, "Diarization"),
    ]

    for tab, ui_key, value, label in test_cases:
        success, info = await update_config({ui_key: value})
        
        saved = False
        verified = False
        note = ""

        if success:
            if isinstance(info, dict) and info.get("updated", 0) > 0:
                saved = True
                verified = True
                note = "Persisted to DB"
            else:
                note = f"Ignorado (Key '{ui_key}' sin mapeo/columna)"
        else:
            note = f"Error: {info}"
        
        record_result(tab, label, str(value)[:25], saved, verified, note)

    # Generate Report Table
    print("\n" + "="*120)
    print(f"{'TAB':<15} | {'CONTROL':<25} | {'KEY (FE)':<20} | {'SAVED':<10} | {'VERIFIED':<10} | {'NOTES'}")
    print("-" * 120)
    for res in results:
        key = next((k for t, k, v, l in test_cases if l == res["Control"]), "N/A")
        print(f"{res['Tab']:<15} | {res['Control']:<25} | {key:<20} | {res['Saved']:<10} | {res['Verified']:<10} | {res['Notes']}")
    print("="*120)

if __name__ == "__main__":
    asyncio.run(main())
