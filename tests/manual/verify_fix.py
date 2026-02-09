
import requests
import json
import logging
import time
import os
from dotenv import load_dotenv

# --- CONFIG ---
load_dotenv()
BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("ADMIN_API_KEY", "secret123")
LOG_LEVEL = logging.INFO

# --- LOGGING SETUP ---
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("VERIFIER")

def get_current_config():
    """Fetch the full agent config (server source of truth)."""
    urls = [
        f"{BASE_URL}/api/config",
        f"{BASE_URL}/api/config/api/config"
    ]
    for url in urls:
        try:
            resp = requests.get(url, headers={"X-API-Key": API_KEY})
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch config from {url}: {e}")
    return {}

def update_twilio_config(payload):
    """Send PATCH request to /api/config/twilio (Dynamic)."""
    # Try Standard first
    url = f"{BASE_URL}/api/config/twilio"
    resp = requests.patch(url, json=payload, headers={"X-API-Key": API_KEY})
    if resp.status_code == 404:
        # Try Double Prefix
        url = f"{BASE_URL}/api/config/api/config/twilio"
        resp = requests.patch(url, json=payload, headers={"X-API-Key": API_KEY})
    
    try:
        if resp.status_code in [200, 202]:
            return resp.status_code, resp.json()
        return resp.status_code, resp.text
    except:
        return resp.status_code, resp.text

def verify_tab(tab_name, test_cases):
    """
    Generic verification for a tab.
    test_cases: List of (FrontendKey, ValueToSend, BackendKeyToCheck, ReadableName)
    """
    logger.info(f"🔍 Verifying Tab: {tab_name}")
    
    # 1. Build Payload
    payload = {case[0]: case[1] for case in test_cases}
    
    # 2. Update Config
    status, result = update_twilio_config(payload)
    if status not in [200, 202]:
        logger.error(f"❌ Update Failed for {tab_name}: {status} - {result}")
        return

    # 3. Read Back
    full_config = get_current_config()
    
    # 4. Verify Each Control
    print(f"\n{'CONTROL':<30} | {'SENT':<20} | {'SAVED':<20} | {'STATUS':<10}")
    print("-" * 90)
    
    for sent_key, sent_val, backend_key, label in test_cases:
        saved_val = full_config.get(backend_key)
        
        # Normalization for comparison
        match = False
        if sent_val == saved_val:
            match = True
        elif str(sent_val) == str(saved_val): # Handle int vs float
            match = True
        elif isinstance(sent_val, dict) and isinstance(saved_val, str):
            # JSON stored as string sometimes? Or vice versa?
            pass 
        elif sent_val is None and saved_val == "":
            match = True

        status_icon = "✅ OK" if match else "❌ FAIL"
        if not match and saved_val is None:
             status_icon = "❌ IGNORED"

        print(f"{label:<30} | {str(sent_val):<20} | {str(saved_val):<20} | {status_icon}")

def main():
    print("================================================================================")
    print("   TWILIO PROFILE FIX VERIFICATION (Transcriptor & Tools Only)")
    print("================================================================================")

    # 3. TRANSCRIPTOR (Phone)
    verify_tab("Transcriptor", [
        ("sttProvider", "deepgram", "stt_provider_phone", "STT Provider"),
        ("sttLang", "es-ES", "stt_language_phone", "STT Language"),
        ("sttSmartFormatting", False, "stt_smart_formatting_phone", "Smart Format"), # Careful with aliases
        ("inputMin", 5, "input_min_characters_phone", "Input Min Chars")
    ])

    # 4. TOOLS (Phone Specific?)
    verify_tab("Tools", [
        ("toolsSchema", {"test": "twilio"}, "tools_schema_phone", "Tools Schema"), # Alias?
        ("asyncTools", True, "async_tools_phone", "Async Tools"), # Assuming shared? Or ignored? Expect IGNORED if not in schema.
        ("toolServerUrl", "https://hook.twilio.com", "tool_server_url_phone", "Server URL")
    ])

if __name__ == "__main__":
    main()
