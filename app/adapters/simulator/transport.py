import base64
import json
from typing import Any, Dict
from fastapi import WebSocket
from app.ports.transport import AudioTransport

class SimulatorTransport(AudioTransport):
    """
    Adapter for the Browser Simulator using FastAPI WebSocket.
    """
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def send_audio(self, audio_data: bytes, sample_rate: int = 8000) -> None:
        # Simulator expects base64 audio in a specific JSON format
        # It handles 16khz usually, but orchestrator decides logic. 
        # Here we just transport.
        try:
            b64 = base64.b64encode(audio_data).decode("utf-8")
            # print(f"Sending Audio: {len(b64)} chars") # Verbose debug
            await self.websocket.send_text(json.dumps({"type": "audio", "data": b64}))
        except Exception as e:
            print(f"SimulatorTransport Send Error: {e}")
            pass

    async def send_json(self, data: Dict[str, Any]) -> None:
        try:
            await self.websocket.send_text(json.dumps(data))
        except Exception:
            pass

    def set_stream_id(self, stream_id: str) -> None:
        # Simulator doesn't strictly need stream_id in messages, 
        # but we can store it or include it if 'debug' events need it.
        pass

    async def close(self) -> None:
        # We don't necessarily close the WS here as routes might manage it, 
        # but if we needed to:
        # await self.websocket.close()
        pass
