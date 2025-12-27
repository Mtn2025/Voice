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

@router.post("/telenyx/incoming-call")
async def incoming_call_telenyx(request: Request):
    """
    Handle Telenyx Call Control Webhooks (Native).
    """
    try:
        data = await request.json()
        event_type = data.get("data", {}).get("event_type")
        payload = data.get("data", {}).get("payload", {})
        call_control_id = payload.get("call_control_id")

        logging.info(f"📞 TELNYX EVENT: {event_type} | ID: {call_control_id}")


        if not call_control_id:
            return Response(status_code=200)

        telenyx_api_url = f"https://api.telnyx.com/v2/calls/{call_control_id}/actions"
        headers = {
            "Authorization": f"Bearer {settings.TELENYX_API_KEY}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            if event_type == "call.initiated":
                # ANSWER THE CALL
                logging.info(f"⚡ Answering Call {call_control_id}")
                resp = await client.post(
                    f"{telenyx_api_url}/answer",
                    headers=headers,
                    json={"stream_track": "both_tracks"} # Ensure we hear both? Usually inbound.
                )
                if resp.status_code != 200:
                    logging.error(f"Failed to answer: {resp.text}")

            elif event_type == "call.answered":
                # START MEDIA STREAM
                protocol = request.url.scheme.replace("http", "ws")
                host = request.url.netloc
                # Hardcode WSS if behind proxy?
                if "localhost" not in host and "127.0.0.1" not in host:
                    protocol = "wss" # Force secure in prod
                
                stream_url = f"{protocol}://{host}/api/v1/ws/media-stream?client=telenyx"
                
                logging.info(f"🌊 Starting Media Stream to: {stream_url}")
                resp = await client.post(
                    f"{telenyx_api_url}/media_start",
                    headers=headers,
                    json={
                        "stream_url": stream_url,
                        "stream_track": "inbound_track",
                        # "media_config": {"input_codec": "PCMU", "output_codec": "PCMU"} # Optional in some versions
                    }
                )
                if resp.status_code != 200:
                    logging.error(f"Failed to start media: {resp.text}")

        return Response(status_code=200)

    except Exception as e:
        logging.error(f"Error handling Telenyx webhook: {e}")
        return Response(status_code=500)

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
            
            # DEEP LOGGING
            event_type = msg.get("event")
            # Log structure (masking payload for readability)
            log_msg = msg.copy()
            if "media" in log_msg and "payload" in log_msg["media"]:
                log_msg["media"]["payload"] = f"<BASE64 DATA len={len(msg['media']['payload'])}>"
            logging.warning(f"📥 WS RECEIVED | Event: {event_type} | Data: {json.dumps(log_msg)}")

            # STREAM ID RECOVERY (Critical for Telenyx)
            if not orchestrator.stream_id and "stream_id" in msg:
                 # Telenyx sends stream_id in every ID
                 logging.warning(f"🔄 Recovered Stream ID from '{event_type}': {msg['stream_id']}")
                 orchestrator.stream_id = msg['stream_id']
                 if orchestrator.call_db_id is None:
                     orchestrator.call_db_id = await db_service.create_call(orchestrator.stream_id)

            if msg["event"] == "start":
                # Ensure we see the RAW start payload to find the ID
                logging.warning(f"🔍 START EVENT RAW: {data}") 
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


