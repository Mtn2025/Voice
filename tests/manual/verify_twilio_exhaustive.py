
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

def get_working_url(suffix):
    """Try single and double prefix to handle server state."""
    urls = [
        f"{BASE_URL}/api/config{suffix}",             # Correct
        f"{BASE_URL}/api/config/api/config{suffix}"  # Old Double Prefix
    ]
    for url in urls:
        try:
            # We use OPTIONS or a lightweight check if possible, or just try PATCH
            # For detection we might need a GET? But /twilio is PATCH only.
            # So we just return the URL and let the caller try.
            # Actually, let's assume the first one that doesn't 404 logic is hard for PATCH.
            # Let's try to DETECT via generic config endpoint first.
            pass
        except:
            pass
    return urls # Wrapper logic needed in update

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

def check_history_endpoint():
    """Detect History endpoint."""
    urls = [
        f"{BASE_URL}/api/history/rows",
        f"{BASE_URL}/api/history/api/history/rows" # Double prefix
    ]
    for url in urls:
        try:
            r = requests.get(url, headers={"X-API-Key": API_KEY})
            if r.status_code != 404:
                return url, r.status_code
        except:
            pass
    return urls[0], 404

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
    print("   TWILIO PROFILE EXHAUSTIVE VERIFICATION (9 TABS)")
    print("================================================================================")

    # 1. MODEL (Phone)
    verify_tab("Model", [
        ("provider", "groq", "llm_provider_phone", "LLM Provider"),
        ("model", "llama-3.3-70b-versatile", "llm_model_phone", "LLM Model"),
        ("temp", 0.8, "temperature_phone", "Creativity"),
        ("prompt", "Twilio System Prompt Test", "system_prompt_phone", "System Prompt"),
        ("tokens", 300, "max_tokens_phone", "Max Tokens"),
        ("contextWindow", 15, "context_window_phone", "Context Window"),
        ("toolChoice", "required", "tool_choice_phone", "Tool Choice")
    ])

    # 2. VOICE (Phone)
    verify_tab("Voice", [
        ("voiceProvider", "azure", "tts_provider_phone", "TTS Provider"),
        ("voiceId", "es-MX-JorgeNeural", "voice_name_phone", "Voice ID"),
        ("voiceSpeed", 1.1, "voice_speed_phone", "Speed"),
        ("voicePitch", -2, "voice_pitch_phone", "Pitch"),
        ("voiceStyle", "shout", "voice_style_phone", "Style"),
        ("voiceStyleDegree", 1.5, "voice_style_degree_phone", "Style Degree")
    ])

    # 3. TRANSCRIPTOR (Phone)
    verify_tab("Transcriptor", [
        ("sttProvider", "deepgram", "stt_provider_phone", "STT Provider"),
        ("sttLang", "es-ES", "stt_language_phone", "STT Language"),
        ("sttSmartFormatting", False, "stt_smart_formatting_phone", "Smart Format"), # Careful with aliases
        ("inputMin", 5, "input_min_characters_phone", "Input Min Chars")
    ])

    # 4. TOOLS (Phone Specific?)
    # Checking if Twilio schema supports tool settings.
    verify_tab("Tools", [
        ("toolsSchema", {"test": "twilio"}, "tools_schema_phone", "Tools Schema"), # Alias?
        ("asyncTools", True, "async_tools_phone", "Async Tools"), # Assuming shared? Or ignored? Expect IGNORED if not in schema.
        ("toolServerUrl", "https://hook.twilio.com", "tool_server_url_phone", "Server URL")
    ])

    # 5. CAMPAIGNS (Twilio)
    # Does Twilio profile handle campaigns? Usually campaigns are global or outbound.
    verify_tab("Campaigns", [
        ("crmEnabled", True, "crm_enabled", "CRM Enabled"), # Global?
        ("webhookUrl", "https://twilio.webhook.com", "webhook_url", "Webhook URL")
    ])

    # 6. CONNECTIVITY (Twilio Specifics)
    verify_tab("Connectivity", [
        ("twilioAccountSid", "AC_TEST_123", "twilio_account_sid", "Account SID"),
        ("twilioAuthToken", "AUTH_TOKEN_XY", "twilio_auth_token", "Auth Token"),
        ("twilioFromNumber", "+15551234", "twilio_from_number", "From Number"),
        ("sipTrunkUri", "sip.twilio.com", "sip_trunk_uri_phone", "SIP URI")
    ])

    # 7. SYSTEM (Twilio)
    # Checking if system limits can be set per profile or are global.
    verify_tab("System", [
        ("concurrencyLimit", 15, "concurrency_limit", "Concurrency"),
        ("spendLimitDaily", 200.0, "spend_limit_daily", "Spend Limit")
    ])

    # 8. ADVANCED (Phone)
    verify_tab("Advanced", [
        ("silence", 4000, "silence_timeout_ms_phone", "Silence Timeout"),
        ("denoise", False, "enable_denoising_phone", "Denoise"),
        ("backchannel", True, "voice_backchanneling_phone", "Backchannel"), # Alias might be voiceBackchanneling
        ("amdSensitivity", 0.6, "machine_detection_sensitivity_phone", "AMD Sensitivity"),
        ("voicemailMsg", "Deje un mensaje", "voicemail_message_phone", "Voicemail Msg") # Alias?
    ])

    # 9. CHECK HISTORY ENDPOINT
    print(f"\n{'CONTROL':<30} | {'ENDPOINT':<20} | {'STATUS':<20}")
    print("-" * 90)
    hist_url, hist_status = check_history_endpoint()
    status_str = f"✅ {hist_status}" if hist_status == 200 else f"❌ {hist_status}"
    print(f"{'History Endpoint':<30} | {hist_url.replace(BASE_URL, ''):<20} | {status_str:<20}")

if __name__ == "__main__":
    main()
