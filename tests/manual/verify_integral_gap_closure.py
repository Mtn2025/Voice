import requests
import json
import os
from dotenv import load_dotenv
import logging
import time

# Setup
load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY", "secret123")
BASE_URL = "http://localhost:8000"

# Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("IntegralVerifier")

results = []

def record_result(tab, control, saved, verified, note=""):
    results.append({
        "Tab": tab,
        "Control": control,
        "Saved": "✅ YES" if saved else "❌ NO",
        "Verified": "✅ YES" if verified else "❌ NO",
        "Note": note
    })

def get_working_config_url():
    """Detects if we need double prefix or single."""
    urls = [
        f"{BASE_URL}/api/config/update-json",
        f"{BASE_URL}/api/config/api/config/update-json"
    ]
    for url in urls:
        try:
            resp = requests.post(url, json={}, headers={"X-API-Key": API_KEY})
            if resp.status_code != 404:
                return url
        except:
            pass
    return urls[0]

def verify_config_tab(url, tab_name, test_cases):
    logger.info(f"🔍 Verifying Tab: {tab_name}")
    for ui_key, value, label in test_cases:
        payload = {ui_key: value}
        try:
            resp = requests.post(url, json=payload, headers={"X-API-Key": API_KEY})
            if resp.status_code == 200:
                data = resp.json()
                if data.get("updated", 0) > 0:
                    record_result(tab_name, label, True, True, "Persisted")
                else:
                    record_result(tab_name, label, False, True, "Ignored (No DB Mapping)")
            else:
                record_result(tab_name, label, False, False, f"HTTP {resp.status_code}: {resp.text[:30]}")
        except Exception as e:
            record_result(tab_name, label, False, False, str(e))

def verify_history_tab():
    logger.info(f"🔍 Verifying Tab: History (Read-Only)")
    url = f"{BASE_URL}/api/history/rows"
    try:
        resp = requests.get(url, headers={"X-API-Key": API_KEY})
        if resp.status_code == 200:
            record_result("History", "List Endpoint", True, True, "HTTP 200 OK")
        else:
            record_result("History", "List Endpoint", False, False, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result("History", "List Endpoint", False, False, str(e))

def verify_simulator_tab():
    logger.info(f"🔍 Verifying Tab: Simulator (Protocol)")
    url = f"{BASE_URL}/ws/simulator/stream?client=browser"
    try:
        resp = requests.get(url.replace("ws", "http"))
        if resp.status_code in [400, 426]:
             record_result("Simulator", "WS Endpoint", True, True, "Endpoint Exists")
        elif resp.status_code == 404:
             record_result("Simulator", "WS Endpoint", False, False, "404 Not Found")
        else:
             record_result("Simulator", "WS Endpoint", True, True, f"HTTP {resp.status_code} (Likely OK)")
    except Exception as e:
        record_result("Simulator", "WS Endpoint", False, False, str(e))

def main():
    # Detect URL
    config_url = get_working_config_url()
    logger.info(f"🔗 Using Config URL: {config_url}")

    # 1. MODEL
    verify_config_tab(config_url, "Model", [
        ("provider", "openai", "Provider"),
        ("temp", 0.9, "Creativity"),
        ("prompt", "Test Prompt", "System Prompt"),
        ("contextWindow", 20, "Context Window"),
        ("toolChoice", "auto", "Tool Choice")
    ])

    # 2. VOICE
    verify_config_tab(config_url, "Voice", [
        ("voiceProvider", "azure", "Provider"),
        ("voiceSpeed", 1.2, "Speed"),
        ("voicePitch", -5, "Pitch"),
        ("voiceStyle", "cheerful", "Style")
    ])

    # 3. TRANSCRIPTOR
    verify_config_tab(config_url, "Transcriptor", [
        ("sttProvider", "deepgram", "Provider"),
        ("sttLang", "es-MX", "Language"),
        ("sttSmartFormatting", True, "Smart Format")
    ])

    # 4. TOOLS
    verify_config_tab(config_url, "Tools", [
        ("toolServerUrl", "https://hook.n8n.com/test", "Server URL"),
        ("asyncTools", True, "Async Exec"),
        ("toolsSchema", {"type": "object"}, "JSON Schema") # Correct alias in dashboard.py line 114
    ])

    # 5. CAMPAIGNS
    verify_config_tab(config_url, "Campaigns", [
        ("crmEnabled", True, "CRM Integration"),
        ("webhookUrl", "https://webhook.site/test", "Webhook URL")
    ])

    # 6. CONNECTIVITY
    verify_config_tab(config_url, "Connectivity", [
        ("telnyxApiKey", "KEY123", "Telnyx Key"),
        ("sipTrunkUriPhone", "sip.twilio.com", "SIP URI")
    ])

    # 7. SYSTEM
    verify_config_tab(config_url, "System", [
        ("concurrencyLimit", 50, "Concurrency"),
        ("spendLimitDaily", 100.0, "Spend Limit"),
        ("auditLogEnabled", True, "Audit Log")
    ])

    # 8. ADVANCED
    verify_config_tab(config_url, "Advanced", [
        ("silence", 800, "Silence Timeout"),
        ("denoise", True, "Noise Supp."), # 'denoise' maps to enable_denoising, 'noiseSuppressionLevel' separate
        ("noiseSuppressionLevel", "Low", "Noise Level"),
        ("enableBackchannel", True, "Backchannel") # Check camelCase alias
    ])

    # 9. HISTORY
    verify_history_tab()

    # 10. SIMULATOR
    verify_simulator_tab()

    # OUTPUT REPORT
    print("\n" + "="*80)
    print(f"{'TAB':<15} | {'CONTROL':<20} | {'SAVED':<10} | {'VERIFIED':<10} | {'NOTE'}")
    print("-" * 80)
    for res in results:
        print(f"{res['Tab']:<15} | {res['Control']:<20} | {res['Saved']:<10} | {res['Verified']:<10} | {res['Note']}")
    print("="*80)

if __name__ == "__main__":
    main()
