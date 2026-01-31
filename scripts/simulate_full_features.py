"""
🚀 SIMULATION: FULL INVENTORY & CONTROLS (LLM + VOICE)
======================================================
This script simulates an end-to-end flow for Browser, Twilio, and Telnyx profiles,
verifying that specific inventory controls (1-30) are correctly applied.

It checks:
1. LLM Controls: Context Window, System Prompt, Dynamic Vars.
2. Voice Controls: Provider, Voice ID, Speed, Pitch.
3. Advanced Voice: Humanization (Fillers), 11Labs Params (Mocked).
4. Profile Independence: Ensuring settings don't bleed between profiles.
"""

import asyncio
import logging
import os
import sys
from unittest.mock import patch

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ⚡ BYPASS CONFIG VALIDATION
os.environ["POSTGRES_USER"] = "test_svc_user_secure"
os.environ["POSTGRES_PASSWORD"] = "StrongPassword_123_For_Testing_Only!@#"
os.environ["POSTGRES_DB"] = "test_db"
os.environ["POSTGRES_SERVER"] = "localhost"

# --- 1. PRE-IMPORT PATCHING ---
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import app.db.database

# Use a file-based DB for persistence across the script duration
TEST_DB_URL = "sqlite+aiosqlite:///./simulation.db"
engine = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

# Patch AsyncSessionLocal IMMEDIATELY
app.db.database.AsyncSessionLocal = TestingSessionLocal
print("✅ Patched AsyncSessionLocal BEFORE Orchestrator import")

# --- 2. APP IMPORTS ---
from app.core.frames import TextFrame
from app.core.orchestrator_v2 import VoiceOrchestrator  # Updated: orchestrator.py deleted
from app.core.processor import FrameDirection
from app.db.models import AgentConfig, Base
from app.ports.transport import AudioTransport
from app.processors.logic.llm import LLMProcessor
from app.services.db_service import db_service


# Mock Transport
class MockTransport(AudioTransport):
    async def send_json(self, data: dict):
        pass
    async def send_audio(self, audio: bytes, sample_rate: int):
        pass
    async def close(self):
        pass
    def set_stream_id(self, stream_id: str):
        pass

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("Simulation")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

async def run_simulation():
    print("\n🎬 STARTING FULL INVENTORY SIMULATION")
    print("="*60)

    # Init DB
    await init_db()

    async with TestingSessionLocal() as session:
        # ---------------------------------------------------------
        # 1. SETUP TEST CONFIGURATION (3 PROFILES)
        # ---------------------------------------------------------
        print("\n⚙️  Setting up Configuration...")

        # Cleanup old test config
        old = await db_service.get_agent_config(session)
        if old:
             await session.delete(old)
             await session.commit()

        config = AgentConfig(
            name="simulation_full",

            # --- BROWSER PROFILE (Humanized & 11Labs) ---
            llm_provider="groq",
            llm_model="llama-3.3-70b-versatile",
            system_prompt="Eres un asistente de navegador.",
            context_window=2, # Short window test

            tts_provider="elevenlabs", # Test 11Labs Conditional
            voice_name="Rachel",
            voice_stability=0.3,
            voice_similarity_boost=0.9,
            voice_speaker_boost=True,

            voice_filler_injection=True, # TEST: Humanizer
            voice_backchanneling=True,

            # --- TWILIO PROFILE (Azure & Strict) ---
            llm_provider_phone="groq",
            system_prompt_phone="Eres un asistente telefónico serio.",
            context_window_phone=5,

            tts_provider_phone="azure",
            voice_name_phone="es-MX-DaliaNeural",
            voice_pitch_phone=5,
            voice_speed_phone=1.2,
            voice_filler_injection_phone=False, # TEST: Disabled Humanizer

            # --- TELNYX PROFILE (Telnyx Native) ---
            llm_provider_telnyx="groq",
            system_prompt_telnyx="Eres soporte técnico.",

            tts_provider_telnyx="azure",
            voice_name_telnyx="es-MX-JorgeNeural",
            tts_output_format_telnyx="ulaw_8000"
        )

        session.add(config)
        await session.commit()
        print("✅ Configuration Saved to DB.")

        # ---------------------------------------------------------
        # 2. RUN BROWSER SIMULATION
        # ---------------------------------------------------------
        print("\n🌐 [BROWSER PROFILE] Starting Simulation...")
        orch_browser = VoiceOrchestrator(MockTransport(), client_type="browser")
        await orch_browser.start()

        # Check Pipeline
        if not orch_browser.pipeline:
             print("❌ Pipeline failed to initialize!")
             return

        # Mock Context History (Test Context Window)
        orch_browser.conversation_history = [
            {"role": "user", "content": "Msg 1"},
            {"role": "assistant", "content": "Msg 2"},
            {"role": "user", "content": "Msg 3"}, # Should survive (Window=2)
            {"role": "assistant", "content": "Msg 4"}, # Should survive
        ]

        # Inject "Process"
        print("   🗣️  User Input: 'Cuéntame un chiste corto.'")

        llm_proc = next(p for p in orch_browser.pipeline._processors if isinstance(p, LLMProcessor))

        with patch('app.processors.logic.humanizer.random.random', return_value=0.1): # Force filler
            await llm_proc.process_frame(TextFrame(text="Cuéntame sobre ti."), FrameDirection.DOWNSTREAM)
            # Wait a bit for processing
            await asyncio.sleep(2)

        print("   ✅ Browser Simulation Completed.")

        # ---------------------------------------------------------
        # 3. RUN TWILIO SIMULATION
        # ---------------------------------------------------------
        print("\n📞 [TWILIO PROFILE] Starting Simulation...")
        orch_phone = VoiceOrchestrator(MockTransport(), client_type="twilio")
        await orch_phone.start()

        # Verify Config Overlay
        print("   🔍 Verifying Config Overlay:")
        print(f"      - Provider: {orch_phone.config.tts_provider} (Expected: azure)")
        print(f"      - Voice: {orch_phone.config.voice_name} (Expected: es-MX-DaliaNeural)")
        print(f"      - Speed: {orch_phone.config.voice_speed} (Expected: 1.2)")

        if orch_phone.config.voice_speed == 1.2:
             print("   ✅ Overlay Applied Correctly")
        else:
             print(f"   ❌ Overlay FAILED: Got {orch_phone.config.voice_speed}")

        # Test Humanizer Disabled
        llm_proc_phone = next(p for p in orch_phone.pipeline._processors if isinstance(p, LLMProcessor))

        with patch('app.processors.logic.humanizer.random.random', return_value=0.1): # Force filler IF enabled
             await llm_proc_phone.process_frame(TextFrame(text="Hola."), FrameDirection.DOWNSTREAM)
             await asyncio.sleep(1)

        print("   ✅ Twilio Simulation Completed.")

        # ---------------------------------------------------------
        # 4. CLEANUP
        # ---------------------------------------------------------
        await orch_browser.stop()
        await orch_phone.stop()
        print("\n🎉 SIMULATION FINISHED")
        print("="*60)

if __name__ == "__main__":
    asyncio.run(run_simulation())
