import asyncio
import base64
import json

import websockets


async def test_stream():
    uri = "ws://localhost:8000/api/v1/ws/media-stream"
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")

        # 1. Send Start Event
        start_msg = {
            "event": "start",
            "start": {
                "streamSid": "MZ1234567890",
                "callSid": "CA1234567890"
            }
        }
        await websocket.send(json.dumps(start_msg))
        print("Sent Start Event")

        # 2. simulate audio chunks (silence/noise)
        # 160 bytes of mulaw generic silence/noise
        dummy_audio = base64.b64encode(b'\xff' * 160).decode('utf-8')

        media_msg = {
            "event": "media",
            "media": {
                "payload": dummy_audio
            }
        }

        # Send a few chunks
        for _i in range(10):
            await websocket.send(json.dumps(media_msg))
            await asyncio.sleep(0.02) # 20ms

        print("Sent Audio Chunks")

        # 3. Listen for response (Clear or Media)
        # Note: Without a real Azure key active/valid or without speaking real words,
        # we might not get a "recognized" event back, but we can check if connection stays open
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Received: {response}")
        except TimeoutError:
            print("No response received (Expected if no speech recognized)")

        # 4. Stop
        stop_msg = {"event": "stop"}
        await websocket.send(json.dumps(stop_msg))
        print("Sent Stop Event")

if __name__ == "__main__":
    asyncio.run(test_stream())
