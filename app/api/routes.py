from fastapi import APIRouter, WebSocket, Request, Response
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect
import logging
import json
import uuid
import httpx
import asyncio
import time
import base64
from typing import Dict, Any
from urllib.parse import quote
from app.core.orchestrator import VoiceOrchestrator
from app.api.connection_manager import manager
from app.core.config import settings
from app.services.db_service import db_service

router = APIRouter()

# Call state tracking for Telnyx (event-driven flow)
active_calls: Dict[str, Dict[str, Any]] = {}


@router.api_route("/twilio/incoming-call", methods=["GET", "POST"])
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


@router.post("/telnyx/call-control")
async def telnyx_call_control(request: Request):
    """
    Call Control webhook for Telnyx Voice API.
    Handles all call lifecycle events per official Telnyx documentation.
    https://developers.telnyx.com/docs/v2/call-control
    """
    # Log raw request info BEFORE try block
    logging.warning(f"🔍 WEBHOOK RECEIVED | Method: {request.method} | Path: {request.url.path}")
    
    try:
        # Parse webhook payload
        event = await request.json()
        
        # DEBUG: Print entire raw payload
        logging.warning(f"🔍 RAW PAYLOAD: {json.dumps(event, indent=2)}")
        
        # CORRECT STRUCTURE: Telnyx wraps in "data" object
        data = event.get("data", {})
        event_type = data.get("event_type")
        payload = data.get("payload", {})
        call_control_id = payload.get("call_control_id")
        
        logging.warning(f"📞 PARSED | Type: {event_type} | ID: {call_control_id}")
        logging.info(f"📞 Telnyx Event: {event_type} | Call: {call_control_id}")
        
        # Handle call.initiated - Answer call (step 1 of 2)
        if event_type == "call.initiated":
            from_number = payload.get("from")
            to_number = payload.get("to")
            direction = payload.get("direction", "inbound")
            logging.info(f"   From: {from_number} → To: {to_number} | Direction: {direction}")
            
            # Store call state
            active_calls[call_control_id] = {
                "state": "initiated",
                "from": from_number,
                "to": to_number,
                "direction": direction,
                "initiated_at": time.time()
            }
            
            # Answer call only (don't stream yet)
            asyncio.create_task(answer_call(call_control_id, request))
        
        # Handle call.answered - Answer call and start streaming
        elif event_type == "call.answered":
            logging.info(f"📱 Call Answered: {call_control_id}")
            
            if call_control_id in active_calls:
                active_calls[call_control_id]["state"] = "answered"
                active_calls[call_control_id]["answered_at"] = time.time()
                # NOW start streaming (event-driven, not hardcoded delay)
                await start_streaming(call_control_id, request)
                
                # Start noise suppression after call is answered (with error handling)
                logging.warning(f"🎯 [DEBUG] About to create noise suppression task for {call_control_id}")
                async def _run_suppression():
                    try:
                        await start_noise_suppression(call_control_id)
                    except Exception as e:
                        logging.error(f"Noise suppression task failed: {e}")
                        import traceback
                        logging.error(f"Traceback: {traceback.format_exc()}")
                
                asyncio.create_task(_run_suppression())
                logging.warning(f"✅ [DEBUG] Noise suppression task created successfully")
        
        # Handle streaming.started - Streaming is ready
        elif event_type == "streaming.started":
            logging.info(f"🎙️ Streaming Started: {call_control_id}")
            
            if call_control_id in active_calls:
                active_calls[call_control_id]["state"] = "streaming"
                active_calls[call_control_id]["streaming_at"] = time.time()
        
        # Handle streaming.stopped
        elif event_type == "streaming.stopped":
            logging.info(f"🛑 Streaming Stopped: {call_control_id}")
            
            if call_control_id in active_calls:
                active_calls[call_control_id]["state"] = "stream_stopped"
        
        # Handle call.hangup - Cleanup
        elif event_type == "call.hangup":
            hangup_cause = payload.get("hangup_cause", "unknown")
            hangup_source = payload.get("hangup_source", "unknown")
            logging.info(f"📴 Call Hangup: {call_control_id} | Cause: {hangup_cause} | Source: {hangup_source}")
            
            # Cleanup state
            if call_control_id in active_calls:
                duration = time.time() - active_calls[call_control_id].get("initiated_at", time.time())
                logging.info(f"   Call Duration: {duration:.2f}s")
                del active_calls[call_control_id]
        
        # Acknowledge webhook (required by Telnyx)
        return {"status": "received", "event_type": event_type}
    
    except Exception as e:
        logging.error(f"❌ Call Control Error: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return {"status": "error", "message": str(e)}


async def answer_call(call_control_id: str, request: Request):
    """
    Answer call via Telnyx Call Control API.
    Official docs: https://developers.telnyx.com/docs/api/v2/call-control/Call-Commands#CallAnswer
    """
    headers = {
        "Authorization": f"Bearer {settings.TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Build client_state for tracking (recommended by official docs)
    client_state_data = {
        "call_control_id": call_control_id,
        "session_id": str(uuid.uuid4()),
        "timestamp": time.time()
    }
    client_state = base64.b64encode(
        json.dumps(client_state_data).encode()
    ).decode()
    
    answer_url = f"{settings.TELNYX_API_BASE}/calls/{call_control_id}/actions/answer"
    payload = {
        "client_state": client_state
    }
    
    try:
        logging.info(f"📞 Answering call: {call_control_id}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(answer_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            logging.info(f"✅ Call Answered Successfully")
        else:
            logging.error(f"❌ Answer Failed: {response.status_code} - {response.text}")
            # Retry once
            await asyncio.sleep(0.5)
            async with httpx.AsyncClient(timeout=10.0) as client:
                retry_response = await client.post(answer_url, headers=headers, json=payload)
                if retry_response.status_code == 200:
                    logging.info(f"✅ Call Answered (retry)")
                else:
                    logging.error(f"❌ Answer Retry Failed: {retry_response.text}")
    except Exception as e:
        logging.error(f"❌ Answer Exception: {e}")


async def start_streaming(call_control_id: str, request: Request):
    """
    Start media streaming via Telnyx Call Control API.
    Official docs: https://developers.telnyx.com/docs/v2/call-control/streaming-audio-websockets
    """
    # Build WebSocket URL
    host = request.headers.get("host")
    scheme = request.headers.get("x-forwarded-proto", "https")
    ws_scheme = "wss" if scheme == "https" else "ws"
    
    encoded_id = quote(call_control_id, safe='')
    ws_url = f"{ws_scheme}://{host}/api/v1/ws/media-stream?client=telnyx&call_control_id={encoded_id}"
    
    headers = {
        "Authorization": f"Bearer {settings.TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Build client_state for tracking
    client_state_data = {
        "call_control_id": call_control_id,
        "session_id": str(uuid.uuid4()),
        "timestamp": time.time()
    }
    client_state = base64.b64encode(
        json.dumps(client_state_data).encode()
    ).decode()
    
    stream_url = f"{settings.TELNYX_API_BASE}/calls/{call_control_id}/actions/streaming_start"
    payload = {
        "stream_url": ws_url,
        "stream_track": "both_tracks",
        "stream_bidirectional_mode": "rtp",
        "stream_bidirectional_codec": "PCMU",
        "client_state": client_state
    }
    
    try:
        logging.info(f"🎙️ Starting stream: {call_control_id}")
        logging.info(f"   Stream URL: {ws_url}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(stream_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            logging.info(f"✅ Streaming Started Successfully")
        else:
            logging.error(f"❌ Streaming Failed: {response.status_code} - {response.text}")
            # Retry once
            await asyncio.sleep(0.5)
            async with httpx.AsyncClient(timeout=10.0) as client:
                retry_response = await client.post(stream_url, headers=headers, json=payload)
                if retry_response.status_code == 200:
                    logging.info(f"✅ Streaming Started (retry)")
                else:
                    logging.error(f"❌ Streaming Retry Failed: {retry_response.text}")
    except Exception as e:
        logging.error(f"❌ Streaming Exception: {e}")


async def start_noise_suppression(call_control_id: str):
    """
    Enable Telnyx native noise suppression (Krisp) on a call.
    Official docs: https://developers.telnyx.com/docs/api/v2/call-control/Noise-Suppression
    """
    headers = {
        "Authorization": f"Bearer {settings.TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Load suppression config from DB
    try:
        config = await db_service.get_agent_config()
        enable_suppression = getattr(config, 'enable_krisp_telnyx', True)
    except Exception as e:
        logging.warning(f"Could not load noise suppression config: {e}")
        enable_suppression = True
    
    if not enable_suppression:
        logging.info("🔇 Noise suppression disabled in config")
        return
    
    suppression_url = f"{settings.TELNYX_API_BASE}/calls/{call_control_id}/actions/suppression_start"
    payload = {
        "direction": "both"  # inbound, outbound, or both
    }
    
    try:
        logging.info(f"🔇 Starting noise suppression: {call_control_id}")
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(suppression_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            logging.info(f"✅ Noise Suppression Enabled (both directions)")
        else:
            logging.warning(f"⚠️ Noise Suppression Failed: {response.status_code} - {response.text}")
    except Exception as e:
        logging.warning(f"⚠️ Noise Suppression Exception: {e}")


@router.websocket("/ws/media-stream")
async def media_stream(websocket: WebSocket, client: str = "twilio", id: str = None, call_control_id: str = None):
    """
    WebSocket endpoint for bidirectional media streaming.
    Supports both Twilio and Telnyx protocols.
    """
    # Determine client ID
    client_id = call_control_id or id or str(uuid.uuid4())
    logging.warning(f"🔌 WS CONNECTION | Client: {client}, ID: {client_id}")
    
    try:
        await manager.connect(client_id, websocket)
    except Exception as e:
        logging.error(f"Manager connect failed: {e}")
        return
    
    orchestrator = VoiceOrchestrator(websocket, client_type=client)
    
    try:
        await orchestrator.start()
    except Exception as e:
        logging.error(f"Orchestrator start failed: {e}")
        manager.disconnect(client_id, websocket)
        await websocket.close()
        return
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            event_type = msg.get("event")
            
            # Log received events (mask payload for readability)
            import copy
            log_msg = copy.deepcopy(msg)
            if "media" in log_msg and "payload" in log_msg["media"]:
                log_msg["media"]["payload"] = f"<BASE64 DATA len={len(msg['media']['payload'])}>"
            # Only log non-media events to reduce spam (media events happen every 20ms)
            if event_type != "media":
                logging.warning(f"📥 WS Event: {event_type} | Data: {json.dumps(log_msg)}")
            
            if msg["event"] == "connected":
                logging.info(f"🔗 WebSocket Connected")
            
            elif msg["event"] == "start":
                start_data = msg.get('start', {})
                
                # Extract stream ID (protocol-agnostic)
                stream_sid = (
                    start_data.get('streamSid') or  # Twilio
                    start_data.get('stream_id') or   # Telnyx (in start)
                    msg.get('stream_id') or          # Telnyx (root level)
                    start_data.get('callSid') or     # Fallback
                    str(uuid.uuid4())                # Last resort
                )
                
                logging.info(f"🎙️ Stream Started: {stream_sid}")
                orchestrator.stream_id = stream_sid
                
                # Extract media format (Telnyx provides this)
                media_format = start_data.get('media_format', {})
                encoding = media_format.get('encoding', 'PCMU')
                sample_rate = media_format.get('sample_rate', 8000)
                channels = media_format.get('channels', 1)
                
                orchestrator.audio_encoding = encoding
                logging.info(f"🎧 Media Format: {encoding} @ {sample_rate}Hz, {channels}ch")
                
                # Validate format for Telnyx
                if client == "telnyx" and (encoding != "PCMA" or sample_rate != 8000):
                    logging.warning(f"⚠️ Unexpected Telnyx format: {encoding} @ {sample_rate}Hz")
                
                # Create call DB record
                if orchestrator.call_db_id is None:
                    orchestrator.call_db_id = await db_service.create_call(orchestrator.stream_id)
            
            elif msg["event"] == "media":
                payload = msg["media"]["payload"]
                await orchestrator.process_audio(payload)
            
            elif msg["event"] == "mark":
                if msg.get("mark") == "speech_ended":
                    logging.info("🔊 Client Playback Finished")
                    orchestrator.last_interaction_time = time.time()
                    orchestrator.is_bot_speaking = False
            
            elif msg["event"] == "stop":
                logging.info("🛑 Stream Stopped")
                break
            
            elif msg["event"] == "client_interruption":
                logging.warning("⚡ Client Interruption (Local VAD)")
                await orchestrator.handle_interruption(text="[LOCAL_VAD_INTERRUPTION]")
            
            elif msg["event"] == "vad":
                # Telnyx Voice Activity Detection (Native)
                vad_data = msg.get("vad", {})
                is_speech = vad_data.get("is_speech", False)
                confidence = vad_data.get("confidence", 0.0)
                
                logging.info(f"🎤 VAD | Speech: {is_speech} | Confidence: {confidence:.2f}")
                
                if not is_speech or confidence < 0.7:
                    logging.info("⚠️ VAD: Low confidence, likely background noise")
            
            elif msg["event"] == "clear":
                logging.info("🧹 Clear Buffer Command")
                # Clear any queued audio
            
            elif msg["event"] == "vad_stats":
                rms = msg.get("rms", 0.0)
                orchestrator.update_vad_stats(rms)
    
    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected: {client} (ID: {client_id})")
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        import traceback
        logging.error(f"{traceback.format_exc()}")
    finally:
        manager.disconnect(client_id, websocket)
        await orchestrator.stop()
        
        # Save call to DB
        if orchestrator.call_db_id:
            await db_service.end_call(orchestrator.call_db_id)
        
        try:
            await websocket.close()
        except RuntimeError:
            pass
