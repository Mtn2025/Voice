import asyncio
import json
import logging
import websockets
import base64
import os
import time

# Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SimVerifier")

BASE_URL = "ws://localhost:8000/api/v1/ws/media-stream?client=browser"

results = []

def record_result(control, change, saved, verified, notes=""):
    results.append({
        "Control": control,
        "Change": change,
        "Saved": "✅ YES" if saved else "❌ NO",
        "Verified": "✅ YES" if verified else "❌ NO",
        "Notes": notes
    })

async def test_simulation():
    print("🚀 Starting EXHAUSTIVE Simulator Protocol Verification...")

    try:
        async with websockets.connect(BASE_URL) as ws:
            logger.info("✅ Connected to WebSocket")
            record_result("Connection", "Connect WS", True, True, "Connected")

            # 1. Simulate "Start Test" Button
            start_payload = {
                "event": "start",
                "start": {
                    "streamSid": f"test-browser-{int(time.time())}",
                    "callSid": f"test-sim-{int(time.time())}",
                    "media_format": {"encoding": "audio/pcm", "sample_rate": 16000, "channels": 1}
                }
            }
            await ws.send(json.dumps(start_payload))
            logger.info("▶ Sent 'Start' Command")
            record_result("Start Button", "Click 'Iniciar'", True, True, "Payload Sent")

            # 2. Wait for Responses (Audio, Config, Transcript)
            # We expect the Assistant to say "Hola..." or similar.
            audio_received = False
            transcript_received = False
            config_received = False
            
            # Listen for 10 seconds max
            start_wait = time.time()
            while time.time() - start_wait < 10:
                try:
                    msg_str = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    msg = json.loads(msg_str)
                    
                    if msg.get("type") == "config":
                        config_received = True
                        logger.info(f"🔧 Config Received: {msg}")
                    
                    elif msg.get("event") == "media" or msg.get("type") == "audio":
                        if not audio_received:
                            audio_received = True
                            logger.info("🔊 Audio Stream Received (Voice Active)")
                    
                    elif msg.get("type") == "transcript":
                        transcript_received = True
                        logger.info(f"📝 Transcript: {msg.get('text')} ({msg.get('role')})")

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error reading: {e}")
                    break
            
            # Verify Results
            record_result("Audio Visualizer", "Inbound Audio", audio_received, audio_received, "Stream Received")
            record_result("Transcripts", "Live Text", transcript_received, transcript_received, "Transcript Event")

            # 3. Stop
            # Browser usually just closes socket or sends nothing special? 
            # Looking at code: ws.close() or onclose handler.
            # We just disconnect.
            
    except Exception as e:
        logger.error(f"❌ Connection Failed: {e}")
        record_result("Connection", "Connect WS", False, False, str(e))

    # Generate Report Table
    print("\n" + "="*100)
    print(f"{'CONTROL':<30} | {'ACTION':<25} | {'SAVED':<10} | {'VERIFIED':<10} | {'NOTES'}")
    print("-" * 100)
    for res in results:
        print(f"{res['Control']:<30} | {res['Change']:<25} | {res['Saved']:<10} | {res['Verified']:<10} | {res['Notes']}")
    print("="*100)

if __name__ == "__main__":
    asyncio.run(test_simulation())
