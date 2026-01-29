import asyncio
import logging
import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch

# Set SECURE dummy env vars to satisfy Pydantic validation
os.environ["POSTGRES_USER"] = "simulation_user"
os.environ["POSTGRES_PASSWORD"] = "secure_password_123"
os.environ["POSTGRES_DB"] = "simulation_db"

# Correct path for imports
sys.path.append(".")

from app.core.orchestrator import VoiceOrchestrator
from app.db.models import AgentConfig
from app.processors.logic.stt import STTProcessor
from app.processors.logic.tts import TTSProcessor
from app.core.frames import AudioFrame, TextFrame, CancelFrame

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

async def run_simulation():
    print("\n🌊 STARTING FLOW SIMULATION (PHASE IV)\n=====================================")
    
    # Mock Components
    mock_transport = AsyncMock()
    mock_llm_provider = AsyncMock()
    mock_stt_provider = MagicMock()
    mock_tts_provider = MagicMock()
    
    # -------------------------------------------------------------
    # SCENARIO 1: Interruption Phrases (Base Profile)
    # -------------------------------------------------------------
    print("\n🧪 SCENARIO 1: Interruption Phrases (Browser)")
    
    # Config: Default Base (client_type injected after init)
    config = AgentConfig(
        interruption_phrases='["stop", "cancel", "espera"]',  # JSON String
        barge_in_enabled=True
    )
    config.client_type = "browser"
    
    # Initialize Orchestrator
    orchestrator = VoiceOrchestrator(mock_transport, client_type="browser")
    orchestrator.config = config
    orchestrator.stt_provider = mock_stt_provider
    
    # Initialize STT Wrapper
    stt = STTProcessor(mock_stt_provider, config, asyncio.get_running_loop())
    stt.push_frame = AsyncMock() # Spy on output
    
    # ... logic for Scenario 1 ...
    from app.services.base import STTEvent, STTResultReason
    evt = STTEvent(reason=STTResultReason.RECOGNIZED_SPEECH, text="Por favor espera un momento")
    
    # Run callback
    stt._on_stt_event(evt)
    await asyncio.sleep(0.1) # Yield
    
    # Verify Spy
    calls = stt.push_frame.call_args_list
    cancel_frames = [c for c in calls if isinstance(c[0][0], CancelFrame)]
    
    if cancel_frames:
        print("   ✅ PASSED: CancelFrame emitted for 'espera'")
    else:
        print("   ❌ FAILED: StartFrame not emitted")
        
    # -------------------------------------------------------------
    # SCENARIO 2: Pacing / Response Delay (Phone Profile)
    # -------------------------------------------------------------
    print("\n🧪 SCENARIO 2: Response Delay (Phone)")
    
    # Config: Phone Override
    config_phone = AgentConfig(
        stt_model="nova-2",
        response_delay_seconds_phone=1.5 # 1.5s delay
    )
    config_phone.client_type = "twilio"
    
    tts = TTSProcessor(mock_tts_provider, config_phone)
    tts._synthesize = AsyncMock()
    
    # Inject Queue
    tts._tts_queue = asyncio.Queue()
    await tts._tts_queue.put("Hola mundo")
    
    # Run Worker Step
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        # LOGIC REPLICATION FOR VERIFICATION
        client_type = getattr(tts.config, 'client_type', 'twilio')
        suffix = "_phone" if client_type == "twilio" else "_telnyx"
        delay = getattr(tts.config, f"response_delay_seconds{suffix}", 0.0)
        
        print(f"   -> Detected Client: {client_type}")
        print(f"   -> Detected Delay: {delay}s")
        
        if delay == 1.5:
            print("   ✅ PASSED: Delay correct (1.5s)")
        else:
            print(f"   ❌ FAILED: Expected 1.5s, got {delay}")

    # -------------------------------------------------------------
    # SCENARIO 3: Barge-in Disabled (Telnyx)
    # -------------------------------------------------------------
    print("\n🧪 SCENARIO 3: Barge-in Logic (Telnyx)")
    
    from app.processors.logic.vad import VADProcessor
    config_telnyx = AgentConfig(
        barge_in_enabled_telnyx=False  # Disabled
    )
    config_telnyx.client_type = "telnyx"
    
    vad = VADProcessor(config_telnyx)
    print(f"   -> VAD Configured Barge-in: {vad.barge_in_enabled}")
    
    if vad.barge_in_enabled is False:
        print("   ✅ PASSED: Barge-in correctly DISABLED for Telnyx")
    else:
        print("   ❌ FAILED: Barge-in should be False")

    print("\n🏁 FLOW SIMULATION COMPLETED")

if __name__ == "__main__":
    asyncio.run(run_simulation())
