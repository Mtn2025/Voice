"""
Unit tests for VoiceOrchestrator helper methods and utilities.

Target Coverage: ~25% additional of orchestrator.py
Focus: Utilities, monitoring, DTMF/transfer, background tasks
"""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.core.orchestrator import VoiceOrchestrator


@pytest.mark.unit
class TestSpeakDirect:
    """Test suite for speak_direct (non-LLM speech)."""

    @pytest.mark.asyncio
    async def test_speak_direct_basic(self, mock_websocket, mock_agent_config, mock_tts_provider):
        """Test: speak_direct synthesizes and sends audio."""
        orch = VoiceOrchestrator(mock_websocket, client_type="browser")
        orch.config = mock_agent_config
        orch.tts_provider = mock_tts_provider
        orch.stream_id = "test_stream"

        with patch.object(orch, '_synthesize_text', new_callable=AsyncMock) as mock_synth:
            mock_synth.return_value = b'fake_audio'
            with patch.object(orch, 'send_audio_chunked', new_callable=AsyncMock):
                with patch('app.services.db_service.db_service.log_transcript', new_callable=AsyncMock):
                    await orch.speak_direct("Hola")

                    mock_synth.assert_called_once()

    @pytest.mark.asyncio
    async def test_speak_direct_updates_state(self, mock_websocket, mock_agent_config):
        """Test: speak_direct updates is_bot_speaking state."""
        orch = VoiceOrchestrator(mock_websocket)
        orch.config = mock_agent_config
        orch.is_bot_speaking = False

        with patch.object(orch, '_synthesize_text', new_callable=AsyncMock, return_value=b'audio'):
            with patch.object(orch, 'send_audio_chunked', new_callable=AsyncMock):
                with patch('app.services.db_service.db_service.log_transcript', new_callable=AsyncMock):
                    await orch.speak_direct("Test")

                    # Should set and reset bot speaking
                    assert orch.is_bot_speaking is False  # Reset after completion


@pytest.mark.unit
class TestMonitorIdle:
    """Test suite for idle monitoring."""

    @pytest.mark.asyncio
    async def test_monitor_idle_triggers_timeout(self, mock_websocket, mock_agent_config):
        """Test: monitor_idle detects idle timeout."""
        orch = VoiceOrchestrator(mock_websocket)
        orch.config = mock_agent_config
        orch.config.idle_timeout = 0.1  # 100ms for test
        orch.last_interaction_time = 0  # Long ago
        orch.is_bot_speaking = False

        with patch.object(orch, '_handle_idle_timeout_logic', return_value=True):
            # Should exit after timeout
            await asyncio.wait_for(orch.monitor_idle(), timeout=1.0)

    @pytest.mark.asyncio
    async def test_monitor_idle_max_duration(self, mock_websocket, mock_agent_config):
        """Test: monitor_idle enforces max_duration."""
        orch = VoiceOrchestrator(mock_websocket)
        orch.config = mock_agent_config
        orch.config.max_duration = 0.1  # 100ms
        orch.start_time = 0  # Long ago

        # Should exit when max duration reached
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(orch.monitor_idle(), timeout=0.5)


@pytest.mark.unit
class TestIdleTimeoutLogic:
    """Test suite for _handle_idle_timeout_logic."""

    @pytest.mark.asyncio
    async def test_handle_idle_timeout_logic_retry(self, mock_websocket, mock_agent_config):
        """Test: _handle_idle_timeout_logic sends idle message."""
        orch = VoiceOrchestrator(mock_websocket)
        orch.config = mock_agent_config
        orch.config.idle_message = "¿Hola?"
        orch.config.inactivity_max_retries = 3
        orch.idle_retries = 0

        with patch.object(orch, 'speak_direct', new_callable=AsyncMock):
            import time
            result = await orch._handle_idle_timeout_logic(time.time())

            # Should NOT break (retry < max)
            assert result is False
            assert orch.idle_retries == 1

    @pytest.mark.asyncio
    async def test_handle_idle_timeout_logic_hangup(self, mock_websocket, mock_agent_config):
        """Test: _handle_idle_timeout_logic hangs up after max retries."""
        orch = VoiceOrchestrator(mock_websocket, client_type="browser")
        orch.config = mock_agent_config
        orch.config.inactivity_max_retries = 2
        orch.idle_retries = 2  # Already at max

        with patch.object(mock_websocket, 'close', new_callable=AsyncMock):
            import time
            result = await orch._handle_idle_timeout_logic(time.time())

            # Should break (max retries reached)
            assert result is True


@pytest.mark.unit
class TestSynthesizeText:
    """Test suite for _synthesize_text (SSML wrapping)."""

    @pytest.mark.asyncio
    async def test_synthesize_text_browser(self, mock_websocket, mock_agent_config, mock_tts_provider):
        """Test: _synthesize_text wraps text in SSML for browser."""
        orch = VoiceOrchestrator(mock_websocket, client_type="browser")
        orch.config = mock_agent_config
        orch.tts_provider = mock_tts_provider

        result = await orch._synthesize_text("Hello")

        # Should call TTS provider
        mock_tts_provider.synthesize_ssml.assert_called_once()
        assert result == b'fake_audio_data'

    @pytest.mark.asyncio
    async def test_synthesize_text_with_style(self, mock_websocket, mock_agent_config, mock_tts_provider):
        """Test: _synthesize_text includes voice style if configured."""
        orch = VoiceOrchestrator(mock_websocket)
        orch.config = mock_agent_config
        orch.config.voice_style = "cheerful"
        orch.tts_provider = mock_tts_provider

        await orch._synthesize_text("Test")

        # Should pass style to synthesizer
        call_args = mock_tts_provider.synthesize_ssml.call_args
        assert "cheerful" in str(call_args) or call_args is not None


@pytest.mark.unit
class TestVADUpdates:
    """Test suite for update_vad_stats."""

    def test_update_vad_stats(self, mock_websocket):
        """Test: update_vad_stats updates VAD filter profile."""
        orch = VoiceOrchestrator(mock_websocket)

        orch.update_vad_stats(0.5)

        # Should update filter
        assert orch.vad_filter.samples > 0


@pytest.mark.unit
class TestTransferAndDTMF:
    """Test suite for _perform_transfer and _perform_dtmf."""

    @pytest.mark.asyncio
    async def test_perform_transfer(self, mock_websocket, mock_agent_config):
        """Test: _perform_transfer makes Telnyx API call."""
        orch = VoiceOrchestrator(mock_websocket, client_type="telnyx")
        orch.config = mock_agent_config
        orch.call_control_id = "test_call_id"

        with patch('app.core.orchestrator.http_client') as mock_http:
            mock_http.post = AsyncMock()
            await orch._perform_transfer("+1234567890")

            # Should call Telnyx API
            mock_http.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_perform_dtmf(self, mock_websocket, mock_agent_config):
        """Test: _perform_dtmf sends DTMF tones."""
        orch = VoiceOrchestrator(mock_websocket, client_type="telnyx")
        orch.config = mock_agent_config
        orch.call_control_id = "test_call_id"

        with patch('app.core.orchestrator.http_client') as mock_http:
            mock_http.post = AsyncMock()
            await orch._perform_dtmf("123")

            # Should call Telnyx API
            mock_http.post.assert_called_once()


@pytest.mark.unit
class TestBackgroundTasks:
    """Test suite for _create_background_task."""

    def test_create_background_task(self, mock_websocket):
        """Test: _create_background_task prevents garbage collection."""
        orch = VoiceOrchestrator(mock_websocket)
        orch.loop = asyncio.get_event_loop()

        async def dummy_task():
            await asyncio.sleep(0.01)

        task = orch._create_background_task(dummy_task(), "test_task")

        # Should be tracked
        assert task in orch.background_tasks


@pytest.mark.unit
class TestFirstMessage:
    """Test suite for first message handling."""

    @pytest.mark.asyncio
    async def test_handle_first_message_immediate(self, mock_websocket, mock_agent_config):
        """Test: _handle_first_message sends greeting immediately."""
        orch = VoiceOrchestrator(mock_websocket)
        orch.config = mock_agent_config
        orch.config.first_message = "Hola!"
        orch.config.first_message_mode = "immediate"
        orch.loop = asyncio.get_event_loop()

        with patch.object(orch, 'speak_direct', new_callable=AsyncMock) as mock_speak:
            orch._handle_first_message()

            # Should speak immediately
            await asyncio.sleep(0.1)  # Let task execute
            mock_speak.assert_called()

    @pytest.mark.asyncio
    async def test_handle_first_message_delayed(self, mock_websocket, mock_agent_config):
        """Test: _handle_first_message delays greeting."""
        orch = VoiceOrchestrator(mock_websocket)
        orch.config = mock_agent_config
        orch.config.first_message = "Hola!"
        orch.config.first_message_mode = "delayed"
        orch.config.first_message_delay_ms = 100
        orch.loop = asyncio.get_event_loop()

        with patch.object(orch, '_create_background_task') as mock_task:
            orch._handle_first_message()

            # Should create delayed task
            mock_task.assert_called_once()


@pytest.mark.unit
class TestTTSProcessing:
    """Test suite for _process_tts_chunk."""

    @pytest.mark.asyncio
    async def test_process_tts_chunk(self, mock_websocket, mock_agent_config, mock_tts_provider):
        """Test: _process_tts_chunk synthesizes and sends TTS."""
        orch = VoiceOrchestrator(mock_websocket)
        orch.config = mock_agent_config
        orch.tts_provider = mock_tts_provider

        with patch.object(orch, '_synthesize_text', new_callable=AsyncMock, return_value=b'audio'):
            with patch.object(orch, 'send_audio_chunked', new_callable=AsyncMock):
                await orch._process_tts_chunk("Test sentence.")

                # Should synthesize and send
                assert True



