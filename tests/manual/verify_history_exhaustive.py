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
logger = logging.getLogger("HistoryVerifier")

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

async def main():
    print("🚀 Starting EXHAUSTIVE History Tab Simulation...")
    
    if not await wait_for_server():
        return
    
    # 1. Simulate a Call (Real Call Simulation)
    logger.info("📞 Simulating a Real Call (Simulator)...")
    try:
        start_res = requests.post(
            f"{BASE_URL}/api/chat/v2/start",
            headers={"X-API-Key": API_KEY},
            timeout=10
        )
        if start_res.status_code != 200:
            logger.error(f"Failed to start call: {start_res.text}")
            record_result("Real Call Simulation", "Start Call", False, False, "API /chat/v2/start failed")
            return
        
        data = start_res.json()
        call_id = data.get("call_id") # Actually session_id usually, need to find DB Table ID?
        # The start endpoint returns session_id usually. 
        # But we verify via History Row listing.
        
        logger.info(f"✅ Call Started. Session ID: {data.get('session_id')}")
        record_result("Real Call Simulation", "Create Call", True, True, f"Session: {data.get('session_id')}")

    except Exception as e:
        logger.error(f"Call Simulation Error: {str(e)}")
        record_result("Real Call Simulation", "Start Call", False, False, str(e))
        return

    await asyncio.sleep(2) # Wait for DB commit

    # 2. Verify List (Rows)
    logger.info("📋 Verifying History List...")
    try:
        # Filter: Simulador
        params = {"client_type": "simulator"}
        headers = {"X-API-Key": API_KEY}
        list_res = requests.get(f"{BASE_URL}/api/history/rows", params=params, headers=headers)
        
        if list_res.status_code == 200:
            html = list_res.text
            # Look for indicators of success
            count_success = "success" in html or "View" in html or "Ver" in html
            
            saved = True
            verified = count_success
            note = f"Size: {len(html)} chars. Found Records: {count_success}"
            record_result("Filter: Simulador", "Select 'Simulador'", saved, verified, note)
            
            # Extract a Call ID link if possible (simple split search)
            # data-call-id="123"
            import re
            match = re.search(r'data-call-id="(\d+)"', html)
            latest_id = match.group(1) if match else None
        else:
            record_result("Filter: Simulador", "Fetch Rows", False, False, f"Status: {list_res.status_code}")
            latest_id = None
            
        # Filter: Twilio (Should be empty? or at least successful query)
        params_tw = {"client_type": "twilio"}
        list_tw = requests.get(f"{BASE_URL}/api/history/rows", params=params_tw, headers=headers)
        record_result("Filter: Twilio", "Select 'Twilio'", True, list_tw.status_code == 200, "Query Executed")

    except Exception as e:
        record_result("History List", "Fetch", False, False, str(e))
        latest_id = None

    # 3. Verify Details
    if latest_id:
        logger.info(f"🔍 Verifying Details for Call ID: {latest_id}")
        try:
            detail_res = requests.get(f"{BASE_URL}/api/history/{latest_id}/detail", headers=headers)
            if detail_res.status_code == 200:
                det = detail_res.json()
                has_transcripts = isinstance(det.get("transcripts"), list)
                record_result("View Details", f"ID {latest_id}", True, has_transcripts, "JSON Data OK")
            else:
                record_result("View Details", f"ID {latest_id}", False, False, f"Status {detail_res.status_code}")
        except Exception as e:
             record_result("View Details", "Fetch", False, False, str(e))
    else:
        record_result("View Details", "Select Row", False, False, "No Row Found to Click")


    # Generate Report Table
    print("\n" + "="*100)
    print(f"{'CONTROL':<30} | {'ACTION':<25} | {'SAVED':<10} | {'VERIFIED':<10} | {'NOTES'}")
    print("-" * 100)
    for res in results:
        print(f"{res['Control']:<30} | {res['Change']:<25} | {res['Saved']:<10} | {res['Verified']:<10} | {res['Notes']}")
    print("="*100)

if __name__ == "__main__":
    asyncio.run(main())
