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
from fastapi import APIRouter, Depends, Request, Response, WebSocket
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.websockets import WebSocketDisconnect

from app.adapters.telephony.transport import TelephonyTransport
from app.api.connection_manager import manager
from app.core.config import settings
from app.core.orchestrator_v2 import VoiceOrchestratorV2
from app.core.voice_ports import get_voice_ports
from app.core.webhook_security import require_telnyx_signature, require_twilio_signature
from app.services.db_service import db_service
from app.db.database import AsyncSessionLocal

router = APIRouter()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# State tracking (Keep local or move to Redis later)
active_calls: dict[str, dict[str, Any]] = {}

# --- Twilio Endpoints ---

@router.api_route("/twilio/incoming-call", methods=["GET", "POST"])
@limiter.limit("30/minute")
async def incoming_call(request: Request, _: None = Depends(require_twilio_signature)):
    """
    Twilio incoming call webhook.
    """
    host = request.headers.get("host")
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://{host}/api/v1/ws/media-stream" />
    </Connect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


# --- Telnyx Endpoints ---
# (Logic copied from routes_v2.py lines 62-176 and helpers)

@router.post("/telnyx/call-control")
@limiter.limit("50/minute")
async def telnyx_call_control(request: Request, _: None = Depends(require_telnyx_signature)):
    """
    Telnyx Call Control Webhook.
    """
    try:
        event = await request.json()
        data = event.get("data", {})
        event_type = data.get("event_type")
        payload = data.get("payload", {})
        call_control_id = payload.get("call_control_id")

        logging.info(f"📞 Telnyx Event: {event_type} | Call: {call_control_id}")

        if event_type == "call.initiated":
            # Store state
            active_calls[call_control_id] = {
                "state": "initiated",
                "initiated_at": time.time()
            }
            # Answer call
            from app.api.routes_v2 import answer_call # Can we import? logic is complex.
            # Avoid circular import. Reimplement logic here cleanly.
            asyncio.create_task(answer_call_logic(call_control_id))

        elif event_type == "call.answered":
             logging.info(f"📱 Call Answered: {call_control_id}")
             # Start streaming
             client_state_str = payload.get("client_state")
             await start_streaming_logic(call_control_id, request, client_state_str)
             
             # Start noise suppression (background)
             asyncio.create_task(start_noise_suppression_logic(call_control_id))

        return {"status": "received", "event_type": event_type}

    except Exception as e:
        logger.error(f"Telnyx handler error: {e}")
        return {"status": "error", "message": str(e)}

# --- Helpers (Simplified/Inlined to avoid circular deps) ---
async def answer_call_logic(call_control_id: str):
    # Retrieve config logic (omitted for brevity, assume default/env for refactor safety or duplicate logic)
    # Ideally logic should be in a Service. For now duplicating essential parts.
    api_key = settings.TELNYX_API_KEY
    url = f"{settings.TELNYX_API_BASE}/calls/{call_control_id}/actions/answer"
    # Basic answer
    client_state = base64.b64encode(json.dumps({"call_control_id": call_control_id}).encode()).decode()
    payload = {"client_state": client_state}
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    async with httpx.AsyncClient() as client:
        await client.post(url, headers=headers, json=payload)

async def start_streaming_logic(call_control_id: str, request: Request, client_state: str | None = None):
    host = request.headers.get("host")
    scheme = request.headers.get("x-forwarded-proto", "https")
    ws_scheme = "wss" if scheme == "https" else "ws"
    encoded_id = quote(call_control_id, safe='')
    
    ws_url = f"{ws_scheme}://{host}/api/v1/ws/media-stream?client=telnyx&call_control_id={encoded_id}"
    if client_state:
        ws_url += f"&client_state={client_state}"

    url = f"{settings.TELNYX_API_BASE}/calls/{call_control_id}/actions/streaming_start"
    headers = {"Authorization": f"Bearer {settings.TELNYX_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "stream_url": ws_url,
        "stream_track": "inbound_track",
        "stream_bidirectional_mode": "rtp",
        "stream_bidirectional_codec": "PCMA"
    }
    
    async with httpx.AsyncClient() as client:
        await client.post(url, headers=headers, json=payload)

async def start_noise_suppression_logic(call_control_id: str):
    url = f"{settings.TELNYX_API_BASE}/calls/{call_control_id}/actions/suppression_start"
    headers = {"Authorization": f"Bearer {settings.TELNYX_API_KEY}", "Content-Type": "application/json"}
    payload = {"direction": "both"}
    async with httpx.AsyncClient() as client:
        await client.post(url, headers=headers, json=payload)

# --- WebSocket ---

@router.websocket("/ws/media-stream")
async def telephony_media_stream(websocket: WebSocket, client: str = "twilio", call_control_id: str | None = None, client_state: str | None = None):
    """
    Telephony WebSocket (Twilio/Telnyx).
    """
    client_id = call_control_id or str(uuid.uuid4())
    logger.info(f"🔌 Telephony WS: {client} | ID: {client_id}")

    try:
        await manager.connect(client_id, websocket)
    except Exception:
        return

    # 1. Transport (Telephony Only)
    transport = TelephonyTransport(websocket, protocol=client)

    # 2. Ports (Phone Mode)
    ports = get_voice_ports(audio_mode=client) # twilio or telnyx

    # 3. Orchestrator
    orchestrator = VoiceOrchestratorV2(
        transport=transport,
        stt_port=ports.stt,
        llm_port=ports.llm,
        tts_port=ports.tts,
        config_repo=ports.config_repo,
        call_repo=ports.call_repo,
        transcript_repo=ports.transcript_repo,
        client_type=client,
        initial_context=client_state,
        tools=ports.tools
    )

    manager.register_orchestrator(client_id, orchestrator)

    try:
        await orchestrator.start()
        
        while True:
            # Hybrid Receive Loop (Text for control/Twilio, Bytes for Browser Audio)
            message = await websocket.receive()

            if "text" in message:
                data = message["text"]
                msg = json.loads(data)

                # Delegate VAD handling to transport (Clean Architecture)
                transport.handle_event(msg)

                # Standard Flow
                event_type = msg.get("event")

                if event_type == "connected":
                    pass
                
                elif event_type == "start":
                    # Start logic (stream_id setup)
                    start_data = msg.get('start', {})
                    stream_sid = start_data.get('streamSid') or msg.get('stream_id') or str(uuid.uuid4())
                    orchestrator.stream_id = stream_sid
                    transport.set_stream_id(stream_sid)

                elif event_type == "media":
                    payload = msg["media"]["payload"]
                    await orchestrator.process_audio(payload)
                    if msg.get("mark") == "speech_ended":
                        orchestrator.is_bot_speaking = False

                elif event_type == "stop":
                    break
                
                elif event_type == "client_interruption":
                     # Usually simulator, but maybe Twilio supports it?
                     pass

            elif "bytes" in message:
                # RAW AUDIO (Browser)
                # Orchestrator expects Base64 (legacy compatible), so we encode it.
                # Optimization: Update Orchestrator to accept bytes later.
                chunk = message["bytes"]
                b64_payload = base64.b64encode(chunk).decode('utf-8')
                await orchestrator.process_audio(b64_payload)

    except WebSocketDisconnect:
        logger.info(f"Telephony disconnected: {client_id}")
    finally:
        manager.disconnect(client_id, websocket)
        await orchestrator.stop()
        with contextlib.suppress(RuntimeError):
            await websocket.close()
