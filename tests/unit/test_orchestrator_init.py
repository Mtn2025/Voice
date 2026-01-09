"""
Unit tests for VoiceOrchestrator initialization and setup.

Target Coverage: ~15% of orchestrator.py (~200 lines)
Focus: Constructor, start(), stop(), config loading, provider initialization
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.orchestrator import VoiceOrchestrator


@pytest.mark.unit
class TestOrchestratorInit:
    """Test suite for VoiceOrchestrator initialization."""

    def test_init_browser_mode(self, mock_websocket):
        """Test: Orchestrator initializes correctly in browser mode."""
        orch = VoiceOrchestrator(mock_websocket, client_type="browser")

        assert orch.client_type == "browser"
        assert orch.websocket == mock_websocket
        assert orch.conversation_history == []
        assert orch.is_bot_speaking is False
        assert orch.stream_id is None
        assert orch.config is None

        # Check VAD filter initialized
        assert orch.vad_filter is not None

        # Check audio queue created
        assert orch.audio_queue is not None
        assert isinstance(orch.audio_queue, asyncio.Queue)

    def test_init_twilio_mode(self, mock_websocket):
        """Test: Orchestrator initializes correctly in Twilio mode."""
        orch = VoiceOrchestrator(mock_websocket, client_type="twilio")

        assert orch.client_type == "twilio"
        assert orch.websocket == mock_websocket

        # Providers should be None until start() is called
        assert orch.stt_provider is None
        assert orch.llm_provider is None
        assert orch.tts_provider is None

    def test_init_telnyx_mode(self, mock_websocket):
        """Test: Orchestrator initializes correctly in Telnyx mode."""
        orch = VoiceOrchestrator(mock_websocket, client_type="telnyx")

        assert orch.client_type == "telnyx"
        assert orch.user_audio_buffer == bytearray()
        assert orch.bg_loop_buffer is None


@pytest.mark.unit
class TestOrchestratorStart:
    """Test suite for start() method and initialization flow."""

    @pytest.mark.asyncio
    async def test_start_minimal_flow(self, mock_websocket, mock_agent_config, mock_service_factory, mock_db_service):
        """Test: start() completes minimal initialization without errors."""
        orch = VoiceOrchestrator(mock_websocket, client_type="browser")

        # Mock config loading
        mock_db_service.get_agent_config.return_value = mock_agent_config

        with patch.object(orch, '_load_config_from_db', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = None
            orch.config = mock_agent_config

            with patch.object(orch, '_initialize_providers') as mock_init_providers:
                with patch.object(orch, '_setup_stt') as mock_setup_stt:
                    with patch.object(orch, '_handle_first_message'):
                        # Mock recognizer
                        orch.recognizer = MagicMock()
                        orch.recognizer.start_continuous_recognition_async = MagicMock()
                        orch.recognizer.start_continuous_recognition_async.return_value.get = MagicMock()

                        # Mock TTS provider
                        orch.tts_provider = MagicMock()
                        orch.tts_provider.create_synthesizer = MagicMock(return_value=MagicMock())

                        await orch.start()

                        # Verify key initializations
                        assert orch.loop is not None
                        mock_load.assert_called_once()
                        mock_init_providers.assert_called_once()
                        mock_setup_stt.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_config_from_db_success(self, mock_websocket, mock_agent_config, mock_db_service):
        """Test: _load_config_from_db successfully loads configuration."""
        orch = VoiceOrchestrator(mock_websocket)

        # Mock AsyncSessionLocal
        with patch('app.core.orchestrator.AsyncSessionLocal') as mock_session_local:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_local.return_value = mock_session

            mock_db_service.get_agent_config.return_value = mock_agent_config

            await orch._load_config_from_db()

            assert orch.config == mock_agent_config
            mock_db_service.get_agent_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_config_from_db_failure(self, mock_websocket, mock_db_service):
        """Test: _load_config_from_db raises exception on failure."""
        orch = VoiceOrchestrator(mock_websocket)

        with patch('app.core.orchestrator.AsyncSessionLocal') as mock_session_local:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_local.return_value = mock_session

            mock_db_service.get_agent_config.side_effect = Exception("DB connection failed")

            with pytest.raises(Exception, match="DB connection failed"):
                await orch._load_config_from_db()


@pytest.mark.unit
class TestProviderInitialization:
    """Test suite for provider initialization."""

    def test_initialize_providers(self, mock_websocket, mock_agent_config, mock_service_factory):
        """Test: _initialize_providers correctly initializes all providers."""
        orch = VoiceOrchestrator(mock_websocket)
        orch.config = mock_agent_config

        orch._initialize_providers()

        # Verify providers are set
        assert orch.stt_provider is not None
        assert orch.llm_provider is not None
        assert orch.tts_provider is not None

        # Verify ServiceFactory was called correctly
        mock_service_factory.get_stt_provider.assert_called_once_with(mock_agent_config)
        mock_service_factory.get_llm_provider.assert_called_once_with(mock_agent_config)
        mock_service_factory.get_tts_provider.assert_called_once_with(mock_agent_config)

    def test_setup_stt_browser_mode(self, mock_websocket, mock_agent_config, mock_stt_provider):
        """Test: _setup_stt configures STT for browser mode."""
        orch = VoiceOrchestrator(mock_websocket, client_type="browser")
        orch.config = mock_agent_config
        orch.stt_provider = mock_stt_provider
        orch.loop = asyncio.get_event_loop()

        with patch.object(orch, '_load_background_audio'):
            orch._setup_stt()

            # Verify recognizer was created
            assert orch.recognizer is not None
            mock_stt_provider.create_recognizer.assert_called_once()

            # Verify browser-specific silence timeout (500ms)
            call_args = mock_stt_provider.create_recognizer.call_args
            assert call_args.kwargs['segmentation_silence_ms'] == 500

    def test_setup_stt_phone_mode(self, mock_websocket, mock_agent_config, mock_stt_provider):
        """Test: _setup_stt configures STT for phone mode with longer timeout."""
        orch = VoiceOrchestrator(mock_websocket, client_type="twilio")
        orch.config = mock_agent_config
        orch.stt_provider = mock_stt_provider
        orch.loop = asyncio.get_event_loop()

        with patch.object(orch, '_load_background_audio'):
            orch._setup_stt()

            # Verify phone-specific silence timeout (2000ms)
            call_args = mock_stt_provider.create_recognizer.call_args
            assert call_args.kwargs['segmentation_silence_ms'] == 2000


@pytest.mark.unit
class TestOrchestratorStop:
    """Test suite for stop() and cleanup."""

    @pytest.mark.asyncio
    async def test_stop_cleanup(self, mock_websocket):
        """Test: stop() properly cleans up tasks and recognizer."""
        orch = VoiceOrchestrator(mock_websocket)

        # Create mock tasks
        orch.response_task = AsyncMock()
        orch.response_task.done = MagicMock(return_value=False)
        orch.response_task.cancel = MagicMock()

        orch.stream_task = AsyncMock()
        orch.stream_task.done = MagicMock(return_value=False)
        orch.stream_task.cancel = MagicMock()

        orch.monitor_task = AsyncMock()
        orch.monitor_task.done = MagicMock(return_value=False)
        orch.monitor_task.cancel = MagicMock()

        # Mock recognizer
        orch.recognizer = MagicMock()
        orch.recognizer.stop_continuous_recognition = MagicMock()

        await orch.stop()

        # Verify tasks were canceled
        orch.response_task.cancel.assert_called_once()
        orch.stream_task.cancel.assert_called_once()
        orch.monitor_task.cancel.assert_called_once()

        # Verify tasks set to None
        assert orch.response_task is None
        assert orch.stream_task is None
        assert orch.monitor_task is None


@pytest.mark.unit
class TestProfileConfiguration:
    """Test suite for profile overlay logic."""

    def test_apply_profile_overlay_telnyx(self, mock_websocket, mock_agent_config):
        """Test: _apply_profile_overlay applies Telnyx-specific settings."""
        orch = VoiceOrchestrator(mock_websocket, client_type="telnyx")

        # Setup config with Telnyx overrides
        mock_agent_config.llm_model_telnyx = "telnyx-test-model"
        mock_agent_config.voice_name_telnyx = "es-MX-TelnyxVoice"
        mock_agent_config.silence_timeout_ms_telnyx = 3000

        orch.config = mock_agent_config

        orch._apply_profile_overlay()

        # Verify Telnyx settings were applied
        assert orch.config.llm_model == "telnyx-test-model"
        assert orch.config.voice_name == "es-MX-TelnyxVoice"
        assert orch.config.silence_timeout_ms == 3000

    def test_apply_profile_overlay_twilio(self, mock_websocket, mock_agent_config):
        """Test: _apply_profile_overlay applies Twilio-specific settings."""
        orch = VoiceOrchestrator(mock_websocket, client_type="twilio")

        # Setup config with Twilio overrides
        mock_agent_config.llm_model_phone = "twilio-test-model"
        mock_agent_config.voice_name_phone = "es-MX-TwilioVoice"

        orch.config = mock_agent_config

        orch._apply_profile_overlay()

        # Verify Twilio settings were applied
        assert orch.config.llm_model == "twilio-test-model"
        assert orch.config.voice_name == "es-MX-TwilioVoice"


@pytest.mark.unit
class TestBackgroundAudio:
    """Test suite for background audio loading."""

    def test_load_background_audio_none(self, mock_websocket, mock_agent_config):
        """Test: _load_background_audio skips loading when background_sound is 'none'."""
        orch = VoiceOrchestrator(mock_websocket, client_type="twilio")
        orch.config = mock_agent_config
        orch.config.background_sound = "none"

        orch._load_background_audio()

        # Should not load anything
        assert orch.bg_loop_buffer is None

    def test_load_background_audio_browser_skipped(self, mock_websocket, mock_agent_config):
        """Test: _load_background_audio skips for browser (handled client-side)."""
        orch = VoiceOrchestrator(mock_websocket, client_type="browser")
        orch.config = mock_agent_config
        orch.config.background_sound = "office"

        orch._load_background_audio()

        # Browser should skip server-side loading
        assert orch.bg_loop_buffer is None
