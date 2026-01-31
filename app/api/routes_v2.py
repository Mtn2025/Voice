import asyncio
import base64
import contextlib
import json
import logging
import time
import uuid
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.websockets import WebSocketDisconnect

from app.adapters.simulator.transport import SimulatorTransport
from app.adapters.telephony.transport import TelephonyTransport
from app.api.connection_manager import manager
from app.core.auth_simple import verify_api_key
from app.core.config import settings

# V2: Hexagonal Architecture with DI
from app.core.orchestrator_v2 import VoiceOrchestratorV2
from app.core.voice_ports import get_voice_ports
from app.core.webhook_security import require_telnyx_signature, require_twilio_signature
from app.db.database import AsyncSessionLocal  # NEW
from app.services.db_service import db_service

router = APIRouter()

# =============================================================================
# RATE LIMITING - Punto A3
# =============================================================================
# Limiter compartido (se configura en main.py)
limiter = Limiter(key_func=get_remote_address)

# Call state tracking for Telnyx (event-driven flow)
active_calls: dict[str, dict[str, Any]] = {}


@router.api_route("/twilio/incoming-call", methods=["GET", "POST"])
@limiter.limit("30/minute")  # Rate limit: Max 30 calls/minute per IP
async def incoming_call(request: Request, _: None = Depends(require_twilio_signature)):
    """
    Webhook for Twilio to handle incoming calls.
    Returns TwiML to connect the call to a Media Stream.

    Rate Limit: 30 requests/minute per IP
    Security: HMAC signature validation (Punto A4)
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
@limiter.limit("50/minute")  # Rate limit: Max 50 events/minute per IP
async def telnyx_call_control(request: Request, _: None = Depends(require_telnyx_signature)):
    """
    Call Control webhook for Telnyx Voice API.
    Handles all call lifecycle events per official Telnyx documentation.
    https://developers.telnyx.com/docs/v2/call-control

    Rate Limit: 50 requests/minute per IP
    Security: Ed25519 signature validation (Punto A4)
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
            task = asyncio.create_task(answer_call(call_control_id, request))
            # Store task reference to prevent GC (RUF006)
            active_calls[call_control_id]["answer_task"] = task

        # Handle call.answered - Answer call and start streaming
        elif event_type == "call.answered":
            logging.info(f"📱 Call Answered: {call_control_id}")

            if call_control_id in active_calls:
                active_calls[call_control_id]["state"] = "answered"
                active_calls[call_control_id]["answered_at"] = time.time()
                # Get client_state (Context) if available
                client_state_str = payload.get("client_state")

                # NOW start streaming (event-driven, not hardcoded delay)
                await start_streaming(call_control_id, request, client_state_str)

                # Start noise suppression after call is answered (with error handling)
                logging.warning(f"🎯 [DEBUG] About to create noise suppression task for {call_control_id}")
                async def _run_suppression():
                    try:
                        await start_noise_suppression(call_control_id)
                    except Exception as e:
                        logging.error(f"Noise suppression task failed: {e}")
                        import traceback
                        logging.error(f"Traceback: {traceback.format_exc()}")

                task = asyncio.create_task(_run_suppression())
                # Store task reference (RUF006)
                active_calls[call_control_id]["suppression_task"] = task
                logging.warning("✅ [DEBUG] Noise suppression task created successfully")

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
    amd_mode = 'disabled'
    # Check config for Recording and AMD
    try:
        async with AsyncSessionLocal() as session:
            config = await db_service.get_agent_config(session)
            telnyx_profile = config.get_profile('telnyx')

            if telnyx_profile.enable_recording_telnyx:
                 task = asyncio.create_task(start_recording(call_control_id))
                 # Store in call metadata (RUF006)
                 if call_control_id not in active_calls:
                     active_calls[call_control_id] = {}
                 active_calls[call_control_id]["recording_task"] = task

            amd_mode = telnyx_profile.amd_config_telnyx or 'disabled'
    except Exception as e:
        logging.warning(f"Failed to check recording config: {e}")

    api_key = settings.TELNYX_API_KEY
    try:
        if getattr(config, 'telnyx_api_key', None):
            api_key = config.telnyx_api_key
            logging.info("🔑 Using Telnyx API Key from Dashboard Config")
    except Exception:
        pass

    headers = {
        "Authorization": f"Bearer {api_key}",
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

    # AUDIT FIX: Link AMD Configuration
    if amd_mode and amd_mode != 'disabled':
            payload["answering_machine_detection"] = amd_mode
            logging.info(f"📞 Enabled AMD (Telnyx): {amd_mode}")

    try:
        logging.info(f"📞 Answering call: {call_control_id}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(answer_url, headers=headers, json=payload)

        if response.status_code == 200:
            logging.info("✅ Call Answered Successfully")
        else:
            logging.error(f"❌ Answer Failed: {response.status_code} - {response.text}")
            # Retry once
            await asyncio.sleep(0.5)
            async with httpx.AsyncClient(timeout=10.0) as client:
                retry_response = await client.post(answer_url, headers=headers, json=payload)
                if retry_response.status_code == 200:
                    logging.info("✅ Call Answered (retry)")
                else:
                    logging.error(f"❌ Answer Retry Failed: {retry_response.text}")
    except Exception as e:
        logging.error(f"❌ Answer Exception: {e}")


async def start_streaming(call_control_id: str, request: Request, client_state_inbound: str | None = None):
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

    # Forward inbound context to WebSocket
    if client_state_inbound:
        ws_url += f"&client_state={client_state_inbound}"

    api_key = settings.TELNYX_API_KEY
    # Attempt to load config for API Key if possible (requires DB session, but this is a helper)
    # Ideally should pass key in, but for now we follow pattern.
    # Note: start_streaming is often called without session. Should we pass it?
    # It takes request. We can get session or pass explicit key.
    # For now, fallback to env if db lookup hard (but we want consistency).

    # Check if context inject has it? No.
    # Let's try to get it if reasonable.
    try:
        async with AsyncSessionLocal() as session:
            config = await db_service.get_agent_config(session)
            if getattr(config, 'telnyx_api_key', None):
                api_key = config.telnyx_api_key
    except Exception:
        pass

    headers = {
        "Authorization": f"Bearer {api_key}",
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
        "stream_track": "inbound_track",
        "stream_bidirectional_mode": "rtp",
        "stream_bidirectional_codec": "PCMA",
        "client_state": client_state
    }

    try:
        logging.info(f"🎙️ Starting stream: {call_control_id}")
        logging.info(f"   Stream URL: {ws_url}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(stream_url, headers=headers, json=payload)

        if response.status_code == 200:
            logging.info("✅ Streaming Started Successfully")
        else:
            logging.error(f"❌ Streaming Failed: {response.status_code} - {response.text}")
            # Retry once
            await asyncio.sleep(0.5)
            async with httpx.AsyncClient(timeout=10.0) as client:
                retry_response = await client.post(stream_url, headers=headers, json=payload)
                if retry_response.status_code == 200:
                    logging.info("✅ Streaming Started (retry)")
                else:
                    logging.error(f"❌ Streaming Retry Failed: {retry_response.text}")
    except Exception as e:
        logging.error(f"❌ Streaming Exception: {e}")


async def start_noise_suppression(call_control_id: str):
    """
    Enable Telnyx native noise suppression (Krisp) on a call.
    Official docs: https://developers.telnyx.com/docs/api/v2/call-control/Noise-Suppression
    """
    api_key = settings.TELNYX_API_KEY
    enable_suppression = True

    # Retrieve Config for Krisp
    try:
        async with AsyncSessionLocal() as db:
            config = await db_service.get_agent_config(db)
            telnyx_profile = config.get_profile('telnyx')

            # Default to Krisp enabled unless explicitly disabled
            enable_suppression = telnyx_profile.enable_krisp_telnyx if telnyx_profile.enable_krisp_telnyx is not None else True
            if telnyx_profile.telnyx_api_key:
                api_key = telnyx_profile.telnyx_api_key
    except Exception as e:
        logging.warning(f"Could not load noise suppression config: {e}")
        enable_suppression = True # Default to enabled if config fails

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

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
            logging.info("✅ Noise Suppression Enabled (both directions)")
        else:
            logging.warning(f"⚠️ Noise Suppression Failed: {response.status_code} - {response.text}")
    except Exception as e:
        logging.warning(f"⚠️ Noise Suppression Exception: {e}")


async def start_recording(call_control_id: str):
    """
    Start recording the call via Telnyx Call Control API.
    """
    url = f"{settings.TELNYX_API_BASE}/calls/{call_control_id}/actions/record_start"

    headers = {
        "Authorization": f"Bearer {settings.TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "format": "mp3",
        "channels": "dual" # Record both sides
    }

    try:
        logging.info(f"🎙️ Starting Recording: {call_control_id}")
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, headers=headers, json=payload)

        if resp.status_code == 200:
            logging.info("✅ Rec Started.")
        else:
            logging.error(f"❌ Rec Start Failed: {resp.status_code} - {resp.text}")

    except Exception as e:
        logging.error(f"❌ Rec Exception: {e}")


@router.websocket("/ws/media-stream")
async def media_stream(websocket: WebSocket, client: str = "twilio", id: str | None = None, call_control_id: str | None = None, client_state: str | None = None):
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

    # Select Transport Adapter
    transport = None
    if client == "browser":
         transport = SimulatorTransport(websocket)
    elif client in ["twilio", "telnyx"]:
         transport = TelephonyTransport(websocket, protocol=client)
    else:
         # Fallback
         transport = TelephonyTransport(websocket, protocol="twilio")

    # Build ports once per connection
    ports = get_voice_ports()

    # ✅ DI: Instantiate VoiceOrchestratorV2 with injected ports
    orchestrator = VoiceOrchestratorV2(
        transport=transport,
        stt_port=ports.stt,
        llm_port=ports.llm,
        tts_port=ports.tts,
        config_repo=ports.config_repo,
        call_repo=ports.call_repo,  # ✅ FIX VIOLATION #1
        client_type=client,
        initial_context=client_state,
        tools=ports.tools  # ✅ Module 7: Tool Calling
    )

    # ✅ REGISTER FOR API ACCESS
    manager.register_orchestrator(client_id, orchestrator)

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
                logging.info(f"📥 WS Event: {event_type} | Data: {json.dumps(log_msg)}")
            else:
                 # Debug log for media to confirm flow (User requested "Everything")
                 logging.debug(f"📥 WS Media: {len(msg['media']['payload'])} chars")

            if msg["event"] == "connected":
                logging.info("🔗 WebSocket Connected")

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
                transport.set_stream_id(stream_sid)

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

                # Orchestrator handles DB creation now
                if orchestrator.call_db_id is None:
                     logging.warning("⚠️ [Routes] Call DB ID is None after start (should be set by Orchestrator)")

            elif msg["event"] == "media":
                payload = msg["media"]["payload"]
                await orchestrator.process_audio(payload)

                if msg.get("mark") == "speech_ended":
                    logging.info("🔊 Client Playback Finished")
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

        with contextlib.suppress(RuntimeError):
            await websocket.close()


@router.post("/calls/{call_id}/context")
async def update_call_context(call_id: str, payload: dict):
    """
    Dynamic State Injection (Port 4).
    Allows external systems (n8n, CRM) to inject variables into the
    running LLM context mid-call.

    Payload: {"customer_verified": true, "name": "Juan"}
    """
    # 1. Find the active orchestrator for this call_id
    target_orchestrator = manager.get_orchestrator(call_id)

    if not target_orchestrator:
        return Response(
            content=json.dumps({"status": "error", "message": "Call not found or not active"}),
            status_code=404,
            media_type="application/json"
        )

    # 2. Inject Context
    try:
        success = await target_orchestrator.update_context(payload)
        if success:
             return {"status": "success", "message": "Context updated"}
        return Response(
           content=json.dumps({"status": "error", "message": "Orchestrator pipeline not ready"}),
           status_code=503,
           media_type="application/json"
            )
    except Exception as e:
        return Response(
            content=json.dumps({"status": "error", "message": str(e)}),
            status_code=500,
            media_type="application/json"
        )

@router.post("/calls/test-outbound")
@limiter.limit("5/minute")
async def test_outbound_call(request: Request, _: None = Depends(verify_api_key)):
    """
    Initiate a test outbound call via Telnyx.
    Uses credentials from AgentConfig.
    """
    try:
        body = await request.json()
        target_number = body.get("to")

        if not target_number:
            raise HTTPException(status_code=400, detail="Missing 'to' phone number")

        # 1. Load Config
        async with AsyncSessionLocal() as session:
            config = await db_service.get_agent_config(session)

            telnyx_profile = config.get_profile('telnyx')
            api_key = telnyx_profile.telnyx_api_key or settings.TELNYX_API_KEY
            source_number = telnyx_profile.caller_id_telnyx or telnyx_profile.telnyx_from_number
            connection_id = telnyx_profile.telnyx_connection_id

        if not api_key:
             raise HTTPException(status_code=400, detail="Missing Telnyx API Key in Settings")
        if not source_number:
             raise HTTPException(status_code=400, detail="Missing Caller ID (From Number) in Settings")
        if not connection_id:
             raise HTTPException(status_code=400, detail="Missing Telnyx Connection ID in Settings")

        # 2. Call Telnyx API
        url = "https://api.telnyx.com/v2/calls"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "to": target_number,
            "from": source_number,
            "connection_id": connection_id,
            # "webhook_url": Should already be configured in Telnyx Portal,
            # or we can override if needed: f"https://{request.headers.get('host')}/api/v1/telnyx/call-control"
        }

        logging.info(f"🚀 Initiating Outbound Call to {target_number} via Telnyx")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code in (201, 200):
            data = response.json()
            call_id = data.get("data", {}).get("call_control_id")
            return {"status": "success", "message": "Call Initiated", "call_id": call_id}
        error_msg = response.text
        logging.error(f"❌ Telnyx Outbound Failed: {error_msg}")
        raise HTTPException(status_code=response.status_code, detail=f"Telnyx Error: {error_msg}")

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"❌ Outbound Call Error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
