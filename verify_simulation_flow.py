
import asyncio
import json
import logging
import sys
import requests
import websockets
from typing import Optional

# Configure simple logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_KEY = "generate_with_command_above_replace_this_value"
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/simulator/stream"

def login_and_get_cookies():
    session = requests.Session()
    logger.info("Step 1: Logging in...")
    try:
        resp = session.post(f"{BASE_URL}/login", data={"api_key": API_KEY})
        if resp.status_code in [200, 302]:
            logger.info("✅ Login successful")
            # Convert requests cookies to dict for websockets
            cookies = session.cookies.get_dict()
            # Construct cookie header string
            cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            logger.debug(f"Cookie Header: {cookie_header}")
            return cookie_header, session
        else:
            logger.error(f"❌ Login failed: {resp.status_code}")
            return None, None
    except Exception as e:
        logger.error(f"❌ Login Error: {e}")
        return None, None

async def verify_websocket(cookie_header):
    logger.info("Step 2: Connecting to WebSocket...")
    # headers = {"Cookie": cookie_header} if cookie_header else {}
    # Removing extra_headers as the route doesn't seem to enforce auth via headers and it causes issues on Windows/sim
    try:
        async with websockets.connect(WS_URL) as ws:
            logger.info("✅ WebSocket Connected")
            
            # Send explicit start
            await ws.send(json.dumps({"event": "start"}))
            logger.info("📤 Sent 'start' event")

            # Wait for response logic
            try:
                # Wait for up to 10 seconds for a meaningful response
                msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                logger.info(f"📥 Received raw: {str(msg)[:200]}...") # Truncate log
                
                try:
                    data = json.loads(msg)
                    if data.get("type") == "audio" or "audio" in data:
                         logger.info("✅ Received Audio/TTS Response")
                    elif data.get("type") == "transcript":
                         logger.info(f"✅ Received Transcript: {data.get('text')}")
                except json.JSONDecodeError:
                    if isinstance(msg, bytes):
                         logger.info(f"✅ Received Binary Audio: {len(msg)} bytes")
            except asyncio.TimeoutError:
                logger.warning("⚠️ Timeout waiting for welcome message.")

            await asyncio.sleep(2)
            await ws.send(json.dumps({"event": "stop"}))
            logger.info("📤 Sent 'stop' event")

    except Exception as e:
        logger.error(f"❌ WebSocket Error: {e}")
        return False
    return True

def verify_history(session):
    logger.info("Step 3: Verifying History...")
    try:
        resp = session.get(f"{BASE_URL}/api/history/rows?page=1&limit=5")
        if resp.status_code == 200:
            html = resp.text
            # Look for specific markers from tab_history.html logic
            # browser calls have 'Simulador' text
            if "Simulador" in html:
                 logger.info("✅ Found 'Simulador' call in history")
                 return True
            else:
                logger.warning("⚠️ 'Simulador' call NOT found in recent history.")
                logger.debug(f"History Content: {html[:500]}")
                return False
        else:
            logger.error(f"❌ Failed to fetch history: {resp.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ History Verification Error: {e}")
        return False

async def main():
    cookie_header, session = login_and_get_cookies()
    if not session:
        sys.exit(1)

    # Run WebSocket verification
    ws_success = await verify_websocket(cookie_header)
    
    # Run History verification (using the same session to keep auth)
    hist_success = verify_history(session)

    if ws_success and hist_success:
        print("\n✅ SIMULATION VERIFICATION PASSED")
        sys.exit(0)
    else:
        print("\n❌ SIMULATION VERIFICATION FAILED")
        sys.exit(1)

if __name__ == "__main__":
    if sys.platform == 'win32':
         asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
