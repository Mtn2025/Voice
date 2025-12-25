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

from starlette.websockets import WebSocketDisconnect
from app.api.connection_manager import manager
from app.services.db_service import db_service
import uuid

# ... imports ...

@router.websocket("/ws/media-stream")
async def media_stream(websocket: WebSocket, client: str = "twilio", client_id: str = None):
    logging.info(f"Hit media_stream endpoint. Client: {client}, ID: {client_id}")
    
    if not client_id:
        client_id = str(uuid.uuid4())
        logging.info(f"Generated new client_id: {client_id}")

    try:
        logging.info("Attempting manager.connect...")
        await manager.connect(client_id, websocket)
        logging.info("Manager.connect success.")
    except Exception as e:
        logging.error(f"Manager connect failed: {e!r}")
        return # Exit if connection failed

    orchestrator = VoiceOrchestrator(websocket, client_type=client)
    
    try:
        logging.info("Starting orchestrator...")
        await orchestrator.start()
        logging.info("Orchestrator started.")
    except Exception as e:
        logging.error(f"Orchestrator start failed: {e!r}")
        manager.disconnect(client_id, websocket)
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_text()
            # logging.info(f"Received data: {data[:50]}...") # Optional: Debug verbose
            msg = json.loads(data)
            
            if msg["event"] == "start":
                logging.info(f"Stream started: {msg['start']['streamSid']}")
                orchestrator.stream_id = msg['start']['streamSid']
                if orchestrator.call_db_id is None:
                     # Attempt creation if not done in start (redundancy)
                     logging.info("Creating call DB record from START event...")
                     orchestrator.call_db_id = await db_service.create_call(orchestrator.stream_id)
                
            elif msg["event"] == "media":
                payload = msg["media"]["payload"]
                await orchestrator.process_audio(payload)
                
            elif msg["event"] == "stop":
                logging.info("Stream stopped")
                break
                
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


