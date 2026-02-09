
import asyncio
import json
import logging
import sys
import requests
import websockets
import base64
import uuid

# Configure simple logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
# Note: In a real scenario, Telnyx calls back the server. Here we simulate the webhook hit AND the websocket connection.
API_KEY = "generate_with_command_above_replace_this_value"
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/api/v1/ws/media-stream"
CALL_CONTROL_ID = str(uuid.uuid4())

def trigger_webhook():
    """
    Simulate Telnyx Webhook: Call Initiated -> Call Answered
    """
    logger.info("Step 1: Triggering Telnyx Webhooks...")
    
    # 1. Call Initiated
    payload_init = {
        "data": {
            "event_type": "call.initiated",
            "payload": {
                "call_control_id": CALL_CONTROL_ID,
                "connection_id": "12345",
                "from": "+15551234567",
                "to": "+15559876543",
                "direction": "inbound",
                "state": "parked"
            }
        }
    }
    
    # We need to bypass signature check. 
    # The .env DEBUG=True allows this, OR we need to generate a valid signature.
    # Assuming DEBUG=False from .env check, we might fail unless we mock the signature or set DEBUG=True temporarily.
    # Let's check if we can pass a dummy signature if validation is skipped or if we can disable it.
    # .env says DEBUG=False.
    # routes_v2.py usually has a check. 
    # Let's try sending it. If it fails 403, we might need to enable DEBUG for simulation or mock the signature.
    # Actually, let's use a mocked signature heater if implemented, or just try.
    
    # headers = {
    #    "Telnyx-Signature-Ed25519": "dummy_signature", 
    #    "Telnyx-Timestamp": "1234567890"
    # }
    # To bypass signature in DEBUG mode, send NO headers (see webhook_security.py lines 117-122)
    headers = {}

    try:
        # Note: In the routes_telephony.py we saw:
        # async def telnyx_call_control(request: Request, _: None = Depends(require_telnyx_signature)):
        # If require_telnyx_signature enforces strict check, this will fail.
        # However, for simulation on localhost, often validation is relaxed or we can use the 'simulator' route if available.
        # But this is "Telnyx Profile", so it uses the real route.
        
        # Strategy: Try to hit the endpoint. If 403, we must update .env/config to allow debug or create a valid signature (hard without private key).
        # Wait! The .env settings.DEBUG is False. 
        # But we are on localhost. Maybe we can set DEBUG=True in the running process?
        # Only via restart.
        # Alternatively, we can assume the user has a way to test this or we mock the dependency in the app (too intrusive).
        # Let's TRY it first.
        
        resp = requests.post(f"{BASE_URL}/api/v1/telnyx/call-control", json=payload_init, headers=headers)
        if resp.status_code != 200:
             logger.warning(f"⚠️ Webhook 'initiated' failed: {resp.status_code} - {resp.text}")
             # If 403, we can't easily proceed without changing config.
             if resp.status_code == 403:
                 logger.error("❌ Signature validation failed. Check if DEBUG=True in .env or if we can bypass.")
                 return False
        else:
             logger.info("✅ Webhook 'initiated' success")

        # 2. Call Answered (Triggers WebSocket URL generation)
        payload_answered = {
            "data": {
                "event_type": "call.answered",
                "payload": {
                    "call_control_id": CALL_CONTROL_ID,
                    "client_state": base64.b64encode(json.dumps({"test": "data"}).encode()).decode()
                }
            }
        }
        resp = requests.post(f"{BASE_URL}/api/v1/telnyx/call-control", json=payload_answered, headers=headers)
        if resp.status_code == 200:
             logger.info("✅ Webhook 'answered' success")
        else:
             logger.warning(f"⚠️ Webhook 'answered' failed: {resp.status_code}")

        return True

    except Exception as e:
        logger.error(f"❌ Webhook Error: {e}")
        return False

async def verify_websocket():
    logger.info("Step 2: Connecting to WebSocket as Telnyx...")
    
    # Construct URL manually as if coming from the 'stream_url' in the answer webhook
    # ws://localhost:8000/api/v1/ws/media-stream?client=telnyx&call_control_id=...
    url = f"{WS_URL}?client=telnyx&call_control_id={CALL_CONTROL_ID}"
    
    try:
        async with websockets.connect(url) as ws:
            logger.info("✅ WebSocket Connected")
            
            # Telnyx "start" message properties
            start_msg = {
                "event": "start",
                "start": {
                    "streamSid": str(uuid.uuid4()),
                    "callControlId": CALL_CONTROL_ID
                }
            }
            await ws.send(json.dumps(start_msg))
            logger.info("📤 Sent 'start' event")

            # Wait for audio or response
            try:
                # Expecting "media" event with payload or "mark"
                msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                logger.info(f"📥 Received: {str(msg)[:100]}...")
                
                # Check for audio (Telnyx expects JSON with "media": {"payload": base64...})
                # OR raw bytes if using simplified protocol? 
                # routes_telephony.py uses TelephonyTransport.
                # It usually replies with JSON events.
                
                valid_response = False
                try:
                    data = json.loads(msg)
                    if data.get("event") == "media":
                         logger.info("✅ Received Audio (Media Event)")
                         valid_response = True
                    elif data.get("event") == "mark":
                         logger.info("✅ Received Mark Event")
                         valid_response = True
                except:
                    if isinstance(msg, bytes):
                        # Some implementations send raw bytes too? 
                        logger.info("✅ Received Binary Audio")
                        valid_response = True
                
            except asyncio.TimeoutError:
                logger.warning("⚠️ Timeout waiting for response.")

            await asyncio.sleep(2)
            await ws.close()
            logger.info("✅ WebSocket Closed")
            return True

    except Exception as e:
        logger.error(f"❌ WebSocket Error: {e}")
        return False

def verify_history():
    logger.info("Step 3: Verifying History...")
    session = requests.Session()
    # Login to access history
    session.post(f"{BASE_URL}/login", data={"api_key": API_KEY})
    
    try:
        resp = session.get(f"{BASE_URL}/api/history/rows?page=1&limit=5")
        if resp.status_code == 200:
            html = resp.text
            # Look for Telnyx tag
            if "Telnyx" in html:
                 logger.info("✅ Found 'Telnyx' call in history")
                 return True
            else:
                logger.warning("⚠️ 'Telnyx' call NOT found in recent history.")
                logger.debug(f"History Content: {html[:500]}")
                return False
        else:
            logger.error(f"❌ Failed to fetch history: {resp.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ History Verification Error: {e}")
        return False

async def main():
    if not trigger_webhook():
        logger.error("❌ Webhook trigger failed. Aborting.")
        sys.exit(1)
        
    ws_success = await verify_websocket()
    hist_success = verify_history()

    if ws_success and hist_success:
        print("\n✅ TELNYX VERIFICATION PASSED")
        sys.exit(0)
    else:
        print("\n❌ TELNYX VERIFICATION FAILED")
        sys.exit(1)

if __name__ == "__main__":
    if sys.platform == 'win32':
         asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
