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

@router.websocket("/ws/media-stream")
async def media_stream(websocket: WebSocket, client: str = "twilio"):
    """
    WebSocket endpoint.
    client: 'twilio' or 'browser'
    """
    await websocket.accept()
    logging.info(f"WebSocket connected: {client}")
    
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
                
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        
    finally:
        await orchestrator.stop()
        try:
            # Check safely, though close() typically handles idempotent calls, 
            # sometimes ASGI race conditions occur.
            await websocket.close()
        except RuntimeError:
            pass # Already closed


