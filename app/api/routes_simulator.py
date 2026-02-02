import asyncio
import contextlib
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, status
from fastapi.responses import JSONResponse
from starlette.websockets import WebSocketDisconnect

from app.adapters.simulator.transport import SimulatorTransport
from app.api.connection_manager import manager
from app.core.orchestrator_v2 import VoiceOrchestratorV2
from app.core.voice_ports import get_voice_ports

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/start")
async def start_simulator_session():
    """
    Start a simulator session.
    """
    return JSONResponse({"status": "ready", "message": "Connect to /ws/simulator/stream"})

@router.websocket("/stream")
async def simulator_stream(websocket: WebSocket, client_id: str | None = None):
    """
    Dedicated WebSocket for the Simulator/Browser.
    Path: /ws/simulator/stream
    """
    client_id = client_id or str(uuid.uuid4())
    logger.info(f"🖥️ Simulator Connected | ID: {client_id}")

    try:
        await manager.connect(client_id, websocket)
    except Exception as e:
        logger.error(f"Manager connect failed: {e}")
        return

    # 1. Transport (Simulator)
    transport = SimulatorTransport(websocket)
    
    # 2. Get Ports (Configured for Browser)
    ports = get_voice_ports(audio_mode="browser")

    # 3. Instantiate Orchestrator (Browser Mode)
    orchestrator = VoiceOrchestratorV2(
        transport=transport,
        stt_port=ports.stt,
        llm_port=ports.llm,
        tts_port=ports.tts,
        config_repo=ports.config_repo,
        call_repo=ports.call_repo,
        transcript_repo=ports.transcript_repo,
        client_type="browser",
        tools=ports.tools
    )

    manager.register_orchestrator(client_id, orchestrator)

    try:
        await orchestrator.start()
    except Exception as e:
        logger.error(f"Orchestrator start failed: {e}")
        manager.disconnect(client_id, websocket)
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            # --- Browser/Simulator Specific Event Handling ---
            event = msg.get("event")

            if event == "start":
                # Simulator might send explicit start to match protocol
                pass
            
            elif event == "media":
                # Browser sends audio
                payload = msg.get("media", {}).get("payload")
                if payload:
                    await orchestrator.process_audio(payload)
            
            elif event == "stop":
                break

            elif event == "client_interruption":
                 await orchestrator.handle_interruption(text="[USER_CLICK_INTERRUPT]")

    except WebSocketDisconnect:
        logger.info(f"Simulator disconnected: {client_id}")
    except Exception as e:
        logger.error(f"Simulator WS Error: {e}")
    finally:
        manager.disconnect(client_id, websocket)
        await orchestrator.stop()
        with contextlib.suppress(RuntimeError):
            await websocket.close()
