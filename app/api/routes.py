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


@router.post("/telnyx/call-control")
async def telnyx_call_control(request: Request):
    """
    Call Control webhook for Telnyx.
    Receives JSON events and responds with REST API commands.
    
    Migration from TeXML: Now using pure Call Control API for full compatibility.
    """
    try:
        # Parse JSON event from Telnyx
        event = await request.json()
        
        event_type = event.get("data", {}).get("event_type")
        payload = event.get("data", {}).get("payload", {})
        call_control_id = payload.get("call_control_id")
        
        logging.info(f"📞 Telnyx CC Event: {event_type} | ID: {call_control_id}")
        
        # Handle call.initiated event (new incoming call)
        if event_type == "call.initiated":
            from_number = payload.get("from")
            to_number = payload.get("to")
            logging.info(f"   From: {from_number} → To: {to_number}")
            
            # Answer call and start streaming via REST API
            import asyncio
            asyncio.create_task(answer_and_stream_call(call_control_id, request))
        
        elif event_type == "call.answered":
            logging.info(f"✅ Call Answered | ID: {call_control_id}")
        
        elif event_type == "streaming.started":
            logging.info(f"🎙️ Streaming Started | ID: {call_control_id}")
        
        elif event_type == "streaming.stopped":
            logging.info(f"🛑 Streaming Stopped | ID: {call_control_id}")
        
        elif event_type == "call.hangup":
            logging.info(f"📴 Call Hangup | ID: {call_control_id}")
        
        # Acknowledge receipt (Call Control expects 200 OK)
        return {"status": "received", "event_type": event_type}
    
    except Exception as e:
        logging.error(f"❌ Call Control Error: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return {"status": "error", "message": str(e)}

async def answer_and_stream_call(call_control_id: str, request: Request):
    """
    Answer call and immediately start streaming via Call Control API.
    
    Two-step process:
    1. Send 'answer' command
    2. Send 'streaming_start' command
    """
    import httpx
    from app.core.config import settings
    import asyncio
    
    # Build WebSocket URL
    host = request.headers.get("host")
    scheme = request.headers.get("x-forwarded-proto", "https")
    ws_scheme = "wss" if scheme == "https" else "ws"
    
    from urllib.parse import quote
    encoded_id = quote(call_control_id, safe='')
    ws_url = f"{ws_scheme}://{host}/api/v1/ws/media-stream?client=telnyx&id={encoded_id}"
    
    headers = {
        "Authorization": f"Bearer {settings.TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Step 1: Answer the call
    answer_url = f"{settings.TELNYX_API_BASE}/calls/{call_control_id}/actions/answer"
    
    try:
        logging.info(f"📞 Answering call via API: {call_control_id}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(answer_url, headers=headers, json={})
        
        if response.status_code == 200:
            logging.info(f"✅ Call Answered via API | ID: {call_control_id}")
        else:
            logging.error(f"❌ Answer Failed: {response.status_code} - {response.text}")
            return
    except Exception as e:
        logging.error(f"❌ Answer Exception: {e}")
        return
    
    # Step 2: Wait briefly for call to be fully established
    await asyncio.sleep(0.5)
    
    # Step 3: Start streaming
    stream_url = f"{settings.TELNYX_API_BASE}/calls/{call_control_id}/actions/streaming_start"
    stream_payload = {
        "stream_url": ws_url,
        "stream_track": "both_tracks"
    }
    
    try:
        logging.info(f"🎙️ Starting stream via API: {call_control_id}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(stream_url, headers=headers, json=stream_payload)
        
        if response.status_code == 200:
            logging.info(f"✅ Streaming Started via API | ID: {call_control_id}")
        else:
            logging.error(f"❌ Streaming Failed: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"❌ Streaming Exception: {e}")

# Legacy TeXML endpoint (kept for backward compatibility during migration)
@router.api_route("/telnyx/incoming-call", methods=["GET", "POST"])
async def telnyx_incoming_call_legacy(request: Request):
    """
    LEGACY: TeXML webhook (deprecated).
    Use /telnyx/call-control for new Call Control API.
    """
    logging.warning("⚠️ Legacy TeXML endpoint called. Migrate to /telnyx/call-control")
    return Response(content="<Response><Reject/></Response>", media_type="application/xml")

@router.api_route("/telnyx/events", methods=["GET", "POST"])
async def telnyx_events(request: Request):
    """
    Webhook for Telnyx call progress events (stream-started, stream-stopped, etc.)
    """
    try:
        if request.method == "GET":
            params = dict(request.query_params)
        else:
            # Try JSON first (standard webhooks), fall back to Form (TeXML callbacks)
            try:
                params = await request.json()
            except Exception:
                form_data = await request.form()
                params = dict(form_data)
        
        event_type = params.get("event_type", "unknown")
        # Log everything to debug
        logging.warning(f"🔔 TELNYX EVENT | Type: {event_type} | Data: {params}")
        
        # Respond with 200 to acknowledge receipt
        return {"status": "received", "event_type": event_type}
    
    except Exception as e:
        logging.error(f"❌ Telnyx Event Error: {e}")
        return {"status": "error"}

@router.websocket("/ws/media-stream")
async def media_stream(websocket: WebSocket, client: str = "twilio", id: str = None):
    # 'id' matches the query param we set in the TexML response (...&id={call_leg_id})
    client_id = id
    logging.warning(f"🔌 WS CONNECTION ATTEMPT | Client: {client}, ID: {client_id}")
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


