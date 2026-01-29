import base64
import json
from typing import Any, Dict, Optional
from fastapi import WebSocket
from app.ports.transport import AudioTransport

class TelephonyTransport(AudioTransport):
    """
    Adapter for Telnyx/Twilio WebSockets.
    Wraps raw audio in protocol-specific JSON events.
    """
    def __init__(self, websocket: WebSocket, protocol: str = "twilio"):
        self.websocket = websocket
        self.protocol = protocol # 'twilio' or 'telnyx'
        self.stream_id: Optional[str] = None

    def set_stream_id(self, stream_id: str) -> None:
        self.stream_id = stream_id

            # Protocol Specific Handling
            if self.protocol == "twilio":
                msg = {
                    "event": "media",
                    "streamSid": self.stream_id,
                    "media": {"payload": b64}
                }
            elif self.protocol == "telnyx":
                 msg = {
                    "event": "media",
                    "stream_id": self.stream_id,
                    "media": {
                        "payload": b64,
                        "track": "inbound_track"  # Send audio TO Telnyx (so user hears it)
                    }
                }
            
            await self.websocket.send_text(json.dumps(msg))
        except Exception:
            pass

    async def send_json(self, data: Dict[str, Any]) -> None:
        try:
            # Inject streamID if missing and relevant?
            # Usually 'mark', 'clear' events need streamSid too.
            if self.stream_id:
                if self.protocol == "twilio" and "streamSid" not in data:
                    data["streamSid"] = self.stream_id
                elif self.protocol == "telnyx" and "stream_id" not in data:
                     # Telnyx output events usually don't need stream_id if on same WS, 
                     # but good practice to check logic.
                     pass 

            await self.websocket.send_text(json.dumps(data))
        except Exception:
            pass

    async def close(self) -> None:
        pass
