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
logger = logging.getLogger("ConnectivityVerifier")

results = []

def record_result(control, change, saved, verified, notes=""):
    status_icon = "✅" if "YES" in saved or "N/A" in saved else "❌"
    results.append({
        "Control": control,
        "Change": change,
        "Saved": saved,
        "Verified": verified,
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
    print("🚀 Starting EXHAUSTIVE Connectivity Tab Simulation (Policy Aligned)...")
    
    if not await wait_for_server():
        return
        
    test_cases = [
        # 1. CREDENTIALS (BYOC) - POLICY: ENV ONLY
        ("twilioAccountSid", "AC_TEST_ENV_ONLY", "Twilio Account SID", "Env"),
        ("telnyxApiKey", "KEY_ENV_ONLY", "Telnyx API Key", "Env"),
        
        # 2. SIP & TRUNKING - POLICY: DYNAMIC (ADDED VIA MIGRATION)
        ("sipTrunkUriTelnyx", "sip.simulated.com", "SIP Trunk URI (Telnyx)", "DB"),
        ("sipAuthUserTelnyx", "sim_user_1", "SIP User (Telnyx)", "DB"),
        ("geoRegionTelnyx", "us-west-california", "Geo Region (Telnyx)", "DB"),

        # 3. RECORDING & COMPLIANCE - POLICY: DYNAMIC (EXISTING)
        ("enableRecordingTelnyx", True, "Recording (Telnyx)", "DB"),
        ("twilioRecordingChannels", "mono", "Recording Channels (Twilio)", "DB"),
        ("dtmfListeningEnabledTelnyx", False, "DTMF Listening (Telnyx)", "DB"),
    ]

    for ui_key, value, label, policy in test_cases:
        success, info = await update_config({ui_key: value})
        
        saved_str = "❌ NO"
        verified_str = "❌ NO"
        note = ""

        if success:
            updated_count = info.get("updated", 0)
            
            if policy == "Env":
                # For Env fields, "updated: 0" is the CORRECT behavior (Ignored by DB)
                if updated_count == 0:
                    saved_str = "⚠️ N/A" # Not saved in DB, as expected
                    verified_str = "✅ YES" # Verified it respects policy
                    note = "Ignored (Env Managed)"
                else:
                    saved_str = "❓ YES"
                    verified_str = "❌ NO"
                    note = "Error: Persisted to DB! Should be Env only."
            
            elif policy == "DB":
                # For DB fields, "updated: > 0" is required
                if updated_count > 0:
                    saved_str = "✅ YES"
                    verified_str = "✅ YES"
                    note = "Persisted to DB"
                else:
                    saved_str = "❌ NO"
                    verified_str = "❌ NO"
                    note = f"Failed to save (Missing Column?)"
        else:
            note = f"Error: {info}"
        
        record_result(label, str(value)[:25], saved_str, verified_str, note)

    # Generate Report Table
    print("\n" + "="*110)
    print(f"{'CONTROL':<30} | {'KEY':<20} | {'POLICY':<6} | {'SAVED':<10} | {'VERIFIED':<10} | {'NOTES'}")
    print("-" * 110)
    for res in results:
        t_case = next((t for t in test_cases if t[2] == res["Control"]), None)
        policy = t_case[3] if t_case else "?"
        key = t_case[0] if t_case else "?"
        print(f"{res['Control']:<30} | {key:<20} | {policy:<6} | {res['Saved']:<10} | {res['Verified']:<10} | {res['Notes']}")
    print("="*110)

if __name__ == "__main__":
    asyncio.run(main())
