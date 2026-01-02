from fastapi import APIRouter, WebSocket, Request, Response
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect
import logging
import json
import uuid
import httpx
from app.core.orchestrator import VoiceOrchestrator
from app.api.connection_manager import manager
from app.core.config import settings
from app.services.db_service import db_service

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

@router.api_route("/telnyx/incoming-call", methods=["GET", "POST"])
async def telnyx_incoming_call(request: Request):
    """
    Webhook for Telnyx (TexML).
    Strict implementation: Defaults to PCMU (Mu-Law) and RTP.
    """
    try:
        # 1. Extract Call Control ID / Call SID
        # Telnyx GETs use Query Params. POSTs use Form Data.
        if request.method == "GET":
             params = request.query_params
             call_leg_id = params.get("CallSid") or params.get("CallControlId") or "unknown_get"
             logging.info(f"📞 Telnyx Webhook (GET): ID={call_leg_id}")
        else:
             form_data = await request.form()
             call_leg_id = form_data.get("CallSid") or form_data.get("CallControlId") or "unknown_post"
             logging.info(f"📞 Telnyx Webhook (POST): ID={call_leg_id}")

        host = request.headers.get("host")
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        ws_scheme = "wss" if scheme == "https" else "ws"
        
        # 2. Return TexML
        # Strict Config: bidirectionalCodec="pcmu" (Mu-Law is default/standard)
        # track="both_tracks" (Critical for bidirectional)
        # bidirectionalMode="rtp" (Real-time)
        texml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Answer/>
    <Connect>
        <Stream url="{ws_scheme}://{host}/api/v1/ws/media-stream?client=telnyx&amp;id={call_leg_id}" 
                track="both_tracks" 
                bidirectionalMode="rtp" 
                bidirectionalCodec="pcmu">
        </Stream>
    </Connect>
</Response>"""
        return Response(content=texml, media_type="application/xml")
    
    except Exception as e:
        logging.error(f"❌ Telnyx Webhook Error: {e}")
        return Response(content="<Response><Hangup/></Response>", media_type="application/xml")

@router.websocket("/ws/media-stream")
async def media_stream(websocket: WebSocket, client: str = "twilio", id: str = None):
    # 'id' matches the query param we set in the TexML response (...&id={call_leg_id})
    client_id = id
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
            
            # DEEP LOGGING
            event_type = msg.get("event")
            
            # Log structure (masking payload for readability) WITHOUT mutating original msg
            import copy
            log_msg = copy.deepcopy(msg)
            
            if "media" in log_msg and "payload" in log_msg["media"]:
                log_msg["media"]["payload"] = f"<BASE64 DATA len={len(msg['media']['payload'])}>"
            logging.warning(f"📥 WS RECEIVED | Event: {event_type} | Data: {json.dumps(log_msg)}")

            if msg["event"] == "start":
                # Ensure we see the RAW start payload to find the ID
                logging.warning(f"🔍 START EVENT RAW: {data}") 
                start_data = msg.get('start', {})
                
                # Robust Stream ID Extraction
                # 1. Twilio: 'streamSid' inside 'start'
                stream_sid = start_data.get('streamSid')
                # 2. Telnyx: 'stream_id' inside 'start' (Standard) or Root (Legacy/Variations)
                if not stream_sid:
                     stream_sid = start_data.get('stream_id')
                if not stream_sid:
                     stream_sid = msg.get('stream_id')
                
                if not stream_sid:
                     # Fallback
                     stream_sid = start_data.get('callSid') or str(uuid.uuid4())
                     logging.warning(f"streamSid missing. Using fallback: {stream_sid}")
                
                logging.info(f"Stream started: {stream_sid}")
                orchestrator.stream_id = stream_sid
                
                # Extract Audio Encoding (Telnyx PCMA vs Twilio PCMU)
                media_format = start_data.get('media_format', {})
                encoding = media_format.get('encoding', 'PCMU')
                orchestrator.audio_encoding = encoding
                logging.info(f"🎧 Media Encoding: {encoding}")
                
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
            
            elif msg["event"] == "client_interruption":
                 logging.warning("⚡ [CLIENT] Browser triggered interruption (Local VAD). Syncing state.")
                 # Trigger interruption logic in Orchestrator to cancel speech and reset state
                 # We pass a placeholder text to indicate source
                 await orchestrator.handle_interruption(text="[LOCAL_VAD_INTERRUPTION]")
            
            elif msg["event"] == "vad_stats":
                 rms = msg.get("rms", 0.0)
                 orchestrator.update_vad_stats(rms)
                
    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected: {client} (ID: {client_id})")
    except Exception as e:
        logging.error(f"WebSocket error: {e!r}")
        
    finally:
        manager.disconnect(client_id, websocket)
        await orchestrator.stop()
        
        # Ensure call is saved/ended in DB
        if orchestrator.call_db_id:
            logging.info(f"Saving call end state for ID: {orchestrator.call_db_id}")
            await db_service.end_call(orchestrator.call_db_id)
            
        try:
            await websocket.close()
        except RuntimeError:
            pass # Already closed


