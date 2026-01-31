"""
Verify Orchestrator V2 Refactor.
Checks:
1. Instantiation with mocked ports.
2. Pipeline creation via Factory.
3. Config overlay logic.
4. Lifecycle (Start/Stop).
"""
import asyncio
import logging
import os
import sys
from unittest.mock import AsyncMock, MagicMock

# Validation requires strong passwords
os.environ["POSTGRES_USER"] = "test_user"
os.environ["POSTGRES_PASSWORD"] = "secure_test_password_12345"
os.environ["ADMIN_API_KEY"] = "secure_test_key_12345"
os.environ["APP_ENV"] = "test"
os.environ["AZURE_SPEECH_KEY"] = "mock_key"
os.environ["GROQ_API_KEY"] = "mock_key"

# Adjust path to include app
sys.path.append(".")

import contextlib

from app.core.orchestrator_v2 import VoiceOrchestratorV2
from app.db.models import AgentConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Verifier")

async def test_orchestrator_refactor():
    logger.info("🧪 Starting Orchestrator V2 Refactor Verification")

    # 1. Mock Ports
    mock_transport = AsyncMock()
    mock_stt = AsyncMock()
    mock_llm = AsyncMock()
    mock_tts = AsyncMock()
    mock_call_repo = AsyncMock()
    mock_call_repo.create_call.return_value = 123

    # Mock Config Repo
    mock_config_repo = AsyncMock()
    fake_config = AgentConfig(
        name="test_agent",
        voice_pacing_ms=500, # Initial value
    )
    # Inject legacy/dynamic attributes expected by logic
    fake_config.bg_audio_enabled = True
    fake_config.bg_audio_path = "assets/silence.wav"

    mock_config_repo.get_agent_config.return_value = fake_config

    # 2. Instantiate Orchestrator
    try:
        orchestrator = VoiceOrchestratorV2(
            transport=mock_transport,
            stt_port=mock_stt,
            llm_port=mock_llm,
            tts_port=mock_tts,
            config_repo=mock_config_repo,
            call_repo=mock_call_repo,
            client_type="browser", # specific type to test overlay
            initial_context="e30=" # empty json base64
        )
        logger.info("✅ Instantiation successful")
    except Exception as e:
        logger.error(f"❌ Instantiation failed: {e}")
        return

    # 3. Test Start (Trigger Pipeline Build & Config Overlay)
    try:
        # Mock AudioManager to avoid real IO during test if possible,
        # but our refactor intentionally uses AudioManager.load_background_audio.
        # We Mock the audio_manager instance on the orchestrator logic?
        # No, AudioManager is created inside __init__.
        # We can mock the method on the instance.
        orchestrator.audio_manager.load_background_audio = MagicMock()

        await orchestrator.start()
        logger.info("✅ Start lifecycle successful")

        # 4. Verify Config Overlay
        # Browser should have pacing=0
        if orchestrator.config.voice_pacing_ms == 0:
            logger.info("✅ Config Overlay applied correctly (Browser -> pacing=0)")
        else:
            logger.error(f"❌ Config Overlay failed. Pacing: {orchestrator.config.voice_pacing_ms}")

        # 5. Verify Factory Usage (Pipeline exists)
        if orchestrator.pipeline:
             logger.info(f"✅ Pipeline created successfully: {orchestrator.pipeline}")
        else:
             logger.error("❌ Pipeline is None")

    except Exception as e:
        logger.error(f"❌ Start lifecycle failed: {e}")
        import traceback
        traceback.print_exc()

    # 6. Stop
    await orchestrator.stop()
    logger.info("✅ Stop lifecycle successful")

if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(test_orchestrator_refactor())
