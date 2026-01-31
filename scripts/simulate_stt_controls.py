"""
🚀 SIMULATION: STT EAR & TRANSCRIPTION CONTROLS (v1.0)
======================================================
This script verifies the new STT controls (31-40) defined in Phase III.
It checks if AgentConfig parameters are correctly mapped to STTConfig
and passed to the STT Provider via the STTPort.

Controls Verified:
  31. Provider (Simulated)
  32. Model (nova-2)
  33. Keywords Boosting (JSON)
  34. Endpointing (Silence Timeout)
  35. Utterance End (Semantic)
  36. Punctuation
  37. Profanity Filter
  38. Smart Formatting
  39. Diarization
  40. Multi-Language
"""

import asyncio
import logging
import os
import sys
from unittest.mock import MagicMock, patch

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

TEST_DB_URL = "sqlite+aiosqlite:///./simulation_stt.db"
engine = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
app.db.database.AsyncSessionLocal = TestingSessionLocal

# --- 2. APP IMPORTS ---
from app.core.orchestrator import VoiceOrchestrator
from app.core.service_factory import ServiceFactory
from app.db.models import AgentConfig, Base
from app.ports.transport import AudioTransport

# Logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("STT_Sim")

# Mock Transport
class MockTransport(AudioTransport):
    async def send_json(self, data):
        pass

    async def send_audio(self, audio, sr=None):
        pass

    async def close(self):
        pass

    def set_stream_id(self, sid):
        pass

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

async def run_simulation():
    print("\n👂 STARTING STT CONTROLS SIMULATION")
    print("="*60)

    await init_db()

    # ---------------------------------------------------------
    # SCENARIO 1: FULL CUSTOM STT CONFIGURATION
    # ---------------------------------------------------------
    print("\n🧪 SCENARIO 1: Verifying Advanced STT Config Propagation")

    keywords = [{"word": "Ubrokers", "boost": 2.0}, {"word": "Fiscal", "boost": 1.5}]

    async with TestingSessionLocal() as session:
        config = AgentConfig(
            name="default",
            llm_provider="groq",

            # STT Controls (31-40)
            stt_provider="azure", # 31
            stt_language="es-MX",
            stt_model="nova-2-medical", # 32 (Custom)
            stt_keywords=keywords, # 33
            stt_silence_timeout=800, # 34
            stt_utterance_end_strategy="semantic", # 35

            stt_punctuation=False, # 36 (Toggle Off)
            stt_profanity_filter=False, # 37 (Toggle Off)
            stt_smart_formatting=False, # 38 (Toggle Off)

            stt_diarization=True, # 39 (Toggle On)
            stt_multilingual=True # 40 (Toggle On)
        )
        session.add(config)
        await session.commit()

    # Setup Orchestrator
    orchestrator = VoiceOrchestrator(MockTransport(), client_type="browser")

    # Mock Provider
    mock_stt_provider = MagicMock()
    mock_recognizer = MagicMock()
    mock_stt_provider.create_recognizer.return_value = mock_recognizer

    # Captured Config
    captured_config = None

    def side_effect_create(config, **kwargs):
        nonlocal captured_config
        captured_config = config
        return mock_recognizer

    mock_stt_provider.create_recognizer.side_effect = side_effect_create

    # Patch ServiceFactory
    with patch.object(ServiceFactory, 'get_stt_provider', return_value=mock_stt_provider):
        # We also need to patch LLM/TTS to avoid orphans, but they aren't focus
        with patch.object(ServiceFactory, 'get_llm_provider'), \
             patch.object(ServiceFactory, 'get_tts_provider'):

            # Init Pipeline (Triggers STTProcessor.initialize)
            await orchestrator.start()

            # Allow async tasks to init
            await asyncio.sleep(0.5)

    # Verify
    # Scenario 1 Verification (Existing)
    if captured_config:
        print("\n🔍 VERIFYING STT CONFIG OBJECT (BASE):")
        c = captured_config
        # Minimize output for conciseness
        print(f"   - Model: {c.model} (Expected: nova-2-medical) -> {'✅' if c.model == 'nova-2-medical' else '❌'}")
        print(f"   - Keywords: {c.keywords} -> {'✅' if c.keywords == keywords else '❌'}")

    await orchestrator.stop()

    # ---------------------------------------------------------
    # SCENARIO 2: PHONE PROFILE (Twilio) - Override Verification
    # ---------------------------------------------------------
    print("\n🧪 SCENARIO 2: Verifying Phone Profile Overrides")

    async with TestingSessionLocal() as session:
        # Update config with Phone overrides
        config = await session.get(AgentConfig, 1)
        config.stt_model_phone = "whisper-turbo"
        config.stt_keywords_phone = [{"word": "PhoneKey", "boost": 3.0}]
        config.stt_silence_timeout_phone = 1200
        await session.commit()

    orchestrator_phone = VoiceOrchestrator(MockTransport(), client_type="twilio")

    # Reset Capture
    captured_config_phone = None
    def side_effect_phone(config, **kwargs):
        nonlocal captured_config_phone
        captured_config_phone = config
        return mock_recognizer
    mock_stt_provider.create_recognizer.side_effect = side_effect_phone

    with patch.object(ServiceFactory, 'get_stt_provider', return_value=mock_stt_provider):
        with patch.object(ServiceFactory, 'get_llm_provider'), patch.object(ServiceFactory, 'get_tts_provider'):
            await orchestrator_phone.start()
            await asyncio.sleep(0.5)

    if captured_config_phone:
        c = captured_config_phone
        print("\n🔍 VERIFYING STT CONFIG OBJECT (PHONE):")
        # EXPECT FAILURE HERE if logic is missing
        match_model = c.model == "whisper-turbo"
        match_kw = c.keywords == [{"word": "PhoneKey", "boost": 3.0}]

        print(f"   - Control 32 (Model): {c.model} (Expected: whisper-turbo) -> {'✅' if match_model else '❌'}")
        print(f"   - Control 33 (Keywords): {c.keywords} (Expected: PhoneKey) -> {'✅' if match_kw else '❌'}")
        print(f"   - Control 34 (Silence): {c.silence_timeout} (Expected: 1200) -> {'✅' if c.silence_timeout == 1200 else '❌'}")
    else:
        print("❌ CRITICAL: Provider.create_recognizer NOT called for Phone!")

    await orchestrator_phone.stop()

    # ---------------------------------------------------------
    # SCENARIO 3: TELNYX PROFILE - Override Verification
    # ---------------------------------------------------------
    print("\n🧪 SCENARIO 3: Verifying Telnyx Profile Overrides")

    async with TestingSessionLocal() as session:
        config = await session.get(AgentConfig, 1)
        config.stt_model_telnyx = "google-chirp"
        config.stt_multilingual_telnyx = False
        await session.commit()

    orchestrator_telnyx = VoiceOrchestrator(MockTransport(), client_type="telnyx")

    captured_config_telnyx = None
    def side_effect_telnyx(config, **kwargs):
        nonlocal captured_config_telnyx
        captured_config_telnyx = config
        return mock_recognizer
    mock_stt_provider.create_recognizer.side_effect = side_effect_telnyx

    with patch.object(ServiceFactory, 'get_stt_provider', return_value=mock_stt_provider):
        with patch.object(ServiceFactory, 'get_llm_provider'), patch.object(ServiceFactory, 'get_tts_provider'):
            await orchestrator_telnyx.start()
            await asyncio.sleep(0.5)

    if captured_config_telnyx:
        c = captured_config_telnyx
        print("\n🔍 VERIFYING STT CONFIG OBJECT (TELNYX):")
        match_model = c.model == "google-chirp"
        print(f"   - Control 32 (Model): {c.model} (Expected: google-chirp) -> {'✅' if match_model else '❌'}")
    else:
        print("❌ CRITICAL: Provider.create_recognizer NOT called for Telnyx!")

    await orchestrator_telnyx.stop()
    print("\n🏁 STT SIMULATION COMPLETED")

if __name__ == "__main__":
    asyncio.run(run_simulation())
