"""
Fixtures compartidas para todos los tests.
"""
import os
import sys
from pathlib import Path

# =============================================================================
# CRITICAL: Set env vars BEFORE any app imports
# =============================================================================
os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password_safe")
os.environ.setdefault("POSTGRES_SERVER", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "test_voice_db")
os.environ.setdefault("DEBUG", "True")

import pytest


# =============================================================================
# Environment Setup
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Configure test environment before any tests run.
    Loads .env.test file to satisfy config validation requirements.
    """
    # Load .env.test if exists
    env_test_path = Path(__file__).parent.parent / ".env.test"
    
    if env_test_path.exists():
        # Simple .env parser (no python-dotenv dependency needed)
        with open(env_test_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
    else:
        # Fallback: Set minimal required env vars
        os.environ.setdefault("POSTGRES_USER", "test_user")
        os.environ.setdefault("POSTGRES_PASSWORD", "test_pass_safe")
        os.environ.setdefault("POSTGRES_SERVER", "localhost")
        os.environ.setdefault("POSTGRES_DB", "test_db")
    
    yield
    
    # Cleanup not needed - env vars won't persist outside test process


# =============================================================================
# Mock Fixtures (for future use)
# =============================================================================

@pytest.fixture
def mock_websocket(mocker):
    """Mock FastAPI WebSocket for orchestrator tests."""
    ws = mocker.MagicMock()
    ws.client_state = 1  # CONNECTED
    ws.send_text = mocker.AsyncMock()
    ws.send_bytes = mocker.AsyncMock()
    ws.close = mocker.AsyncMock()
    return ws


@pytest.fixture
def mock_agent_config(mocker):
    """Mock AgentConfig with default test values."""
    config = mocker.MagicMock()
    
    # LLM Settings
    config.llm_provider = "groq"
    config.llm_model = "llama-3.3-70b-versatile"
    config.temperature = 0.7
    config.max_tokens = 500
    config.system_prompt = "You are a test assistant."
    
    # STT Settings
    config.stt_provider = "azure"
    config.stt_language = "es-MX"
    config.silence_timeout_ms = 500
    config.silence_timeout_ms_phone = 2000
    config.initial_silence_timeout_ms = 5000
    config.input_min_characters = 2
    config.interruption_threshold = 5
    config.interruption_threshold_phone = 2
    config.voice_sensitivity = 500
    config.enable_vad = True
    config.enable_denoising = True
    config.hallucination_blacklist = "Pero.,Y...,Mm."
    
    # TTS Settings
    config.voice_name = "es-MX-DaliaNeural"
    config.voice_style = None
    config.voice_speed = 1.0
    config.voice_pacing_ms = 300
    config.voice_pacing_ms_phone = 500
    
    # Flow Control
    config.idle_timeout = 10.0
    config.max_duration = 600
    config.idle_message = "¿Hola?"
    config.inactivity_max_retries = 3
    config.first_message = "Hola!"
    config.first_message_mode = "immediate"
    
    # Features
    config.enable_end_call = True
    config.transfer_phone_number = None
    config.enable_dial_keypad = False
    config.background_sound = "none"
    config.extraction_model = "llama-3.1-8b-instant"
    
    return config


@pytest.fixture
def mock_stt_provider(mocker):
    """Mock STT provider with recognizer."""
    provider = mocker.MagicMock()
    
    # Mock recognizer
    recognizer = mocker.MagicMock()
    recognizer.start_continuous_recognition_async = mocker.MagicMock()
    recognizer.start_continuous_recognition_async.return_value.get = mocker.MagicMock()
    recognizer.stop_continuous_recognition = mocker.MagicMock()
    recognizer.subscribe = mocker.MagicMock()
    recognizer.write = mocker.MagicMock()
    
    provider.create_recognizer = mocker.MagicMock(return_value=recognizer)
    return provider


@pytest.fixture
def mock_llm_provider(mocker):
    """Mock LLM provider with streaming."""
    provider = mocker.MagicMock()
    
    async def mock_stream():
        """Mock LLM stream generator."""
        yield "Hello "
        yield "from "
        yield "test!"
    
    provider.get_stream = mocker.MagicMock(return_value=mock_stream())
    provider.transcribe_audio = mocker.AsyncMock(return_value="test transcription")
    provider.extract_data = mocker.AsyncMock(return_value={"name": "Test"})
    
    return provider


@pytest.fixture
def mock_tts_provider(mocker):
    """Mock TTS provider."""
    provider = mocker.MagicMock()
    
    # Mock synthesizer
    synthesizer = mocker.MagicMock()
    provider.create_synthesizer = mocker.MagicMock(return_value=synthesizer)
    provider.synthesize_ssml = mocker.AsyncMock(return_value=b'fake_audio_data')
    
    return provider


@pytest.fixture
def mock_db_service(mocker):
    """Mock database service."""
    # Patch at module level
    mock_db = mocker.patch('app.services.db_service.db_service', autospec=True)
    mock_db.get_agent_config = mocker.AsyncMock()
    mock_db.create_call = mocker.AsyncMock(return_value=123)
    mock_db.log_transcript = mocker.AsyncMock()
    mock_db.update_call_extraction = mocker.AsyncMock()
    
    return mock_db


@pytest.fixture
def mock_service_factory(mocker, mock_stt_provider, mock_llm_provider, mock_tts_provider):
    """Mock ServiceFactory to return mocked providers."""
    factory_class = mocker.patch('app.core.orchestrator.ServiceFactory')
    
    factory_class.get_stt_provider = mocker.MagicMock(return_value=mock_stt_provider)
    factory_class.get_llm_provider = mocker.MagicMock(return_value=mock_llm_provider)
    factory_class.get_tts_provider = mocker.MagicMock(return_value=mock_tts_provider)
    
    return factory_class


# =============================================================================
# Database Fixtures (for future integration tests)
# =============================================================================

# TODO: Add DB session fixtures when needed for integration tests
# @pytest.fixture
# def test_db_session():
#     """Create in-memory SQLite session for testing."""
#     pass

