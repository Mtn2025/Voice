import asyncio
import websockets
import json
import base64
import time

async def simulate_browser_call():
    uri = "ws://localhost:8000/api/simulator/stream"  # Endpoint from routes_simulator.py @router.websocket("/stream")
    # Wait, in the code it was @router.websocket("/stream") inside routes_simulator.py
    # But where is the router mounted?
    # Usually in main.py. Given file path app/api/routes_simulator.py, prefix likely /api/simulator
    
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            
            # 1. Send START
            start_msg = {
                "event": "start",
                "start": {
                    "streamSid": "sim_text_test",
                    "callSid": "sim_text_call_001",
                    "media_format": {"encoding": "audio/pcm", "sample_rate": 16000, "channels": 1}
                }
            }
            await websocket.send(json.dumps(start_msg))
            print("📤 Sent START")

            # 2. Receive Initial Messages (Wait for Greeting Audio)
            print("👂 Waiting for greeting...")
            audio_count = 0
            start_time = time.time()
            
            # Wait a bit for greeting
            while time.time() - start_time < 5:
                try:
                    msg = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(msg)
                    event = data.get("type") or data.get("event")
                    
                    if event == "audio" or event == "media":
                        audio_count += 1
                        if audio_count % 10 == 0:
                            print(f"   🔊 Received audio chunk {audio_count}")
                    elif event == "config":
                        print(f"   ⚙️ Config received: {data}")
                    elif event == "transcript":
                        print(f"   📝 Transcript: {data.get('role')}: {data.get('text')}")
                except asyncio.TimeoutError:
                    break

            if audio_count > 0:
                print(f"✅ Received {audio_count} audio chunks (Greeting confirmed)")
            else:
                print("⚠️ No greeting audio received (might be configured to wait for user)")

            # 3. Send TEXT INPUT
            print("\n📤 Sending TEXT: 'Hola, esto es una prueba de sistema.'")
            text_msg = {
                "event": "text_input",
                "text": "Hola, esto es una prueba de sistema."
            }
            await websocket.send(json.dumps(text_msg))

            # 4. Wait for Response (Transcript + Audio)
            print("👂 Waiting for AI response...")
            response_audio = 0
            transcript_received = False
            
            start_time = time.time()
            while time.time() - start_time < 10:
                try:
                    msg = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(msg)
                    event = data.get("type") or data.get("event")
                    
                    if event == "transcript":
                        role = data.get("role")
                        text = data.get("text")
                        print(f"   📝 Transcript [{role}]: {text}")
                        if role == "assistant":
                            transcript_received = True
                    elif event == "audio" or event == "media":
                        response_audio += 1
                        if response_audio % 10 == 0:
                            print(f"   🔊 AI Speaking... ({response_audio})")
                    elif event == "debug":
                        if data.get("event") == "llm_latency":
                            print(f"   ⏱️ LLM Latency: {data.get('data', {}).get('duration_ms')}ms")

                    if transcript_received and response_audio > 20:
                        print("✅ AI Response confirmed (Transcript + Audio)")
                        break
                        
                except asyncio.TimeoutError:
                    pass

            # 5. Stop
            print("\n📤 Sending STOP")
            await websocket.send(json.dumps({"event": "stop"}))
            print("✅ Call ended")

    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(simulate_browser_call())
