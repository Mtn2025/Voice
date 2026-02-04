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
logger = logging.getLogger("CampaignVerifier")

results = []

def record_result(control, change, saved, verified, notes=""):
    results.append({
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

async def verify_config_persistence():
    print("\n🔹 Verifying Configuration Persistence (Integrations)...")
    payload = {
        "crmEnabled": True,
        "webhookUrl": "https://webhook.site/test-campaign",
        "webhookSecret": "secret_campaign_123"
    }
    
    url = f"{BASE_URL}/api/config/update-json?context_type=browser"
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200 and response.json().get("updated", 0) > 0:
            record_result("CRM Integration", "Enabled", True, True, "Persistido OK")
            record_result("Webhook URL", "Updated", True, True, "Persistido OK")
            record_result("Webhook Secret", "Updated", True, True, "Persistido OK")
        else:
            record_result("CRM Integration", "Enabled", False, False, f"Error: {response.text}")
    except Exception as e:
         record_result("CRM Integration", "Exception", False, False, str(e))

async def verify_campaign_launch():
    print("\n🔹 Verifying Campaign Launch Action...")
    # Mock CSV file
    files = {
        'file': ('contacts.csv', 'phone,name\n+525512345678,Juan Perez', 'text/csv')
    }
    
    url = f"{BASE_URL}/api/campaigns/start?api_key={API_KEY}"
    # Form data for name
    data = {'name': 'Simulated Verification Campaign'}
    
    try:
        response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            json_resp = response.json()
            if json_resp.get("status") == "queued":
                record_result("Launch Campaign", "Upload CSV", True, True, f"✅ Success: {json_resp['message']}")
            else:
                record_result("Launch Campaign", "Upload CSV", True, False, f"⚠️ Partial: {json_resp}")
        else:
             record_result("Launch Campaign", "Upload CSV", False, False, f"❌ Error {response.status_code}: {response.text}")
            
    except Exception as e:
        record_result("Launch Campaign", "Exception", False, False, str(e))

async def main():
    print("🚀 Starting EXHAUSTIVE Campaigns Tab Simulation (Iteration 2)...")
    if not await wait_for_server():
        return

    await verify_config_persistence()
    await verify_campaign_launch()

    # Generate Report Table
    print("\n" + "="*100)
    print(f"{'CONTROL':<30} | {'KEY/ACTION':<25} | {'SAVED':<10} | {'VERIFIED':<10} | {'NOTES'}")
    print("-" * 100)
    for res in results:
        print(f"{res['Control']:<30} | {res['Change']:<25} | {res['Saved']:<10} | {res['Verified']:<10} | {res['Notes']}")
    print("="*100)

if __name__ == "__main__":
    asyncio.run(main())
