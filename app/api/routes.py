from fastapi import APIRouter, WebSocket, Request, Response
from fastapi.responses import HTMLResponse
import logging
import json
from app.core.orchestrator import VoiceOrchestrator

router = APIRouter()

@router.api_route("/twilio/incoming-call", methods=["GET", "POST"])
async def incoming_call(request: Request):
    """
    Webhook for Twilio to handle incoming calls.
    Returns TwiML to connect the call to a Media Stream.
    Supports GET/POST to be robust against redirects (301 POST->GET) or config errors.
    """
    host = request.headers.get("host")
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://{host}/api/v1/ws/media-stream" />
    </Connect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")

@router.api_route("/telenyx/incoming-call", methods=["GET", "POST"])
async def incoming_call_telenyx(request: Request):
    """
    Webhook for Telenyx (TeXML) to handle incoming calls.
    Returns TeXML to connect the call to a Media Stream.
    """
    host = request.headers.get("host")
    # Strict XML construction
    texml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Response>\n'
        '    <Connect>\n'
        f'        <Stream url="wss://{host}/api/v1/ws/media-stream?client=telenyx" />\n'
        '    </Connect>\n'
        '</Response>'
    )
    return Response(content=texml, media_type="application/xml")

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
                logging.info(f"Received START event payload: {msg}") # DEBUG Payload
                start_data = msg.get('start', {})
                stream_sid = start_data.get('streamSid')
                # Telenyx uses 'stream_id' (snake_case)
                if not stream_sid:
                    stream_sid = start_data.get('stream_id')
                
                if not stream_sid:
                     # Fallback
                     stream_sid = start_data.get('callSid') or start_data.get('call_control_id') or str(uuid.uuid4())
                     logging.warning(f"streamSid/stream_id missing. Using fallback: {stream_sid}")
                
                logging.info(f"Stream started: {stream_sid}")
                orchestrator.stream_id = stream_sid
                if orchestrator.call_db_id is None:
                     # Attempt creation if not done in start (redundancy)
                     logging.info("Creating call DB record from START event...")
                     orchestrator.call_db_id = await db_service.create_call(orchestrator.stream_id)
                
            elif msg["event"] == "media":
                payload = msg["media"]["payload"]
                await orchestrator.process_audio(payload)
                
            elif msg["event"] == "mark":
                 if msg.get("mark") == "speech_ended":
                     import time
                     logging.info("🔊 Client Playback Finished. Resetting Idle Timer.")
                     orchestrator.last_interaction_time = time.time()
                     orchestrator.is_bot_speaking = False

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


