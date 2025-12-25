from fastapi import APIRouter, WebSocket, Request, Response
from fastapi.responses import HTMLResponse
import logging
import json
from app.core.orchestrator import VoiceOrchestrator

router = APIRouter()

@router.post("/twilio/incoming-call")
async def incoming_call(request: Request):
    """
    Webhook for Twilio to handle incoming calls.
    Returns TwiML to connect the call to a Media Stream.
    """
    host = request.headers.get("host")
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://{host}/api/v1/ws/media-stream" />
    </Connect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")

from app.api.connection_manager import manager
import uuid

# ... imports ...

@router.websocket("/ws/media-stream")
async def media_stream(websocket: WebSocket, client: str = "twilio", client_id: str = None):
    """
    WebSocket endpoint.
    client: 'twilio' or 'browser'
    client_id: Unique ID for browser tab/session (to enforce singleton connection)
    """
    # For Twilio, use a random ID or streamSid if possible (Twilio doesn't send query params easily usually, 
    # but we can assume Twilio manages its own unrelated streams). 
    # For Browser, we require/expect client_id.
    if not client_id:
        client_id = str(uuid.uuid4())

    await manager.connect(client_id, websocket)
    logging.info(f"WebSocket connected: {client} (ID: {client_id})")
    
    orchestrator = VoiceOrchestrator(websocket, client_type=client)
    await orchestrator.start()
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg["event"] == "start":
                logging.info(f"Stream started: {msg['start']['streamSid']}")
                orchestrator.stream_id = msg['start']['streamSid']
                
            elif msg["event"] == "media":
                payload = msg["media"]["payload"]
                await orchestrator.process_audio(payload)
                
            elif msg["event"] == "stop":
                logging.info("Stream stopped")
                break
                
from starlette.websockets import WebSocketDisconnect

# ...

    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected: {client} (ID: {client_id})")
    except Exception as e:
        logging.error(f"WebSocket error: {e!r}")
        
    finally:
        manager.disconnect(client_id, websocket)
        await orchestrator.stop()
        try:
            await websocket.close()
        except RuntimeError:
            pass # Already closed


