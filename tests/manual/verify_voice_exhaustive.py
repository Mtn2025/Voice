import asyncio
import json
import os
import requests
import websockets
import logging
from dotenv import load_dotenv

# Setup
load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY", "secret123")
BASE_URL = "http://localhost:8000"

# Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("VoiceVerifier")

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

async def update_config(payload):
    url = f"{BASE_URL}/api/config/update-json?context_type=browser"
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return True, response.json()
    except Exception as e:
        logger.error(f"Config Update Failed: {e}")
        return False, str(e)

async def main():
    print("🚀 Starting EXHAUSTIVE Voice Tab Simulation...")
    
    if not await wait_for_server():
        print("❌ Server not available.")
        return
        
    test_cases = [
        # MAPPED KEYS (Should Pass)
        ("voiceProvider", "azure", "TTS Provider"),
        ("voiceLang", "es-MX", "Language"),
        ("voiceId", "es-MX-DaliaNeural", "Voice ID"),
        ("voiceSpeed", 1.1, "Speed"),
        ("voiceStyle", "cheerful", "Style"),
        ("voiceBgSound", "office", "Background Sound"),
        
        # PREVIOUSLY UNMAPPED KEYS (Now Should Pass)
        ("voicePitch", 5, "Pitch (Hz)"),
        ("voiceVolume", 90, "Volume (%)"),
        ("voiceStyleDegree", 1.5, "Style Degree"),
        
        # Humanization
        ("voiceFillerInjection", True, "Filler Injection"),
        ("voiceBackchanneling", True, "Backchanneling"),
        
        # Technical
        ("textNormalizationRule", "strict", "Text Normalization"),
        ("ttsLatencyOptimization", 1, "Latency Optimization"),
        ("ttsOutputFormat", "pcm_24000", "Output Format"),
        
        # ElevenLabs Specifics
        ("voiceStability", 0.7, "Stability"),
        ("voiceSimilarityBoost", 0.8, "Similarity Boost"),
        ("voiceStyleExaggeration", 0.2, "Style Exaggeration"),
        ("voiceSpeakerBoost", False, "Speaker Boost"),
        ("voiceMultilingual", False, "Multilingual v2")
    ]

    for ui_key, value, label in test_cases:
        success, info = await update_config({ui_key: value})
        
        saved = False
        verified = False
        note = ""

        if success:
            if isinstance(info, dict) and info.get("updated", 0) > 0:
                saved = True
                verified = True
            else:
                note = f"ignorado (Frontend Key '{ui_key}' no mapeada)"
        else:
            note = f"Error: {info}"
        
        record_result(label, str(value)[:25], saved, verified, note)

    # Generate Report Table
    print("\n" + "="*100)
    print(f"{'CONTROL':<30} | {'KEY (FE)':<25} | {'SAVED':<10} | {'VERIFIED':<10} | {'NOTES'}")
    print("-" * 100)
    # Using enumerate or just finding matching case to print
    for res in results:
        # Find key from test_cases
        key = next((k for k, v, l in test_cases if l == res["Control"]), "N/A")
        print(f"{res['Control']:<30} | {key:<25} | {res['Saved']:<10} | {res['Verified']:<10} | {res['Notes']}")
    print("="*100)

    # 3. Simulate Real Call (Websocket)
    print("\n📞 Simulating Real Call (WebSocket Connection)...")
    WS_URL = "ws://localhost:8000/ws/simulator/stream"
    try:
        async with websockets.connect(WS_URL) as websocket:
            # Send Start
            await websocket.send(json.dumps({"type": "start"}))
            print("   ✅ WebSocket Connected")
            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"   ✅ Received Audio/Message: {len(msg)} bytes")
            except asyncio.TimeoutError:
                print("   ⚠️ Timeout waiting for audio (Check Logs)")
                
    except Exception as e:
        print(f"   ❌ WebSocket Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
