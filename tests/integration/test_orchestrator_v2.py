"""Integration tests for VoiceOrchestratorV2 with Managers and Hexagonal DI."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock

from app.core.orchestrator_v2 import VoiceOrchestratorV2
from app.ports.transport import AudioTransport

# ✅ Hexagonal Architecture: Import ports for mocking
from app.domain.ports import STTPort, LLMPort, TTSPort


@pytest.fixture
def mock_stt_port():
    """✅ Create mock STTPort for DI."""
    mock = Mock(spec=STTPort)
    return mock


@pytest.fixture
def mock_llm_port():
    """✅ Create mock LLMPort for DI."""
    mock = Mock(spec=LLMPort)
    return mock


@pytest.fixture
def mock_tts_port():
    """✅ Create mock TTSPort for DI."""
    mock = Mock(spec=TTSPort)
    return mock


@pytest.fixture
def mock_transport():
    """Create mock transport."""
    transport = Mock(spec=AudioTransport)
    transport.send_audio = AsyncMock()
    transport.send_json = AsyncMock()
    return transport


@pytest.fixture
def orchestrator_v2(mock_transport, mock_stt_port, mock_llm_port, mock_tts_port):
    """✅ Create VoiceOrchestratorV2 with DI (mocked ports)."""
    return VoiceOrchestratorV2(
        transport=mock_transport,
        stt_port=mock_stt_port,  # ✅ Injected
        llm_port=mock_llm_port,  # ✅ Injected
        tts_port=mock_tts_port,  # ✅ Injected
        client_type="browser"
    )
        """Test initialization with context data."""
        import base64
        import json
        
        context = {"phone": "+525551234567", "campaign_id": "test-123"}
        context_token = base64.b64encode(json.dumps(context).encode()).decode()
        
        orch = VoiceOrchestratorV2(
            transport=mock_transport,
            client_type="twilio",
            initial_context=context_token
        )
        
        assert orch.initial_context_data == context


class TestAudioManagement:
    """Test audio delegation to AudioManager."""
    
    @pytest.mark.asyncio
    async def test_send_audio_chunked_delegates_to_manager(self, orchestrator_v2):
        """Test that send_audio_chunked delegates to AudioManager."""
        orchestrator_v2.audio_manager.send_audio_chunked = AsyncMock()
        
        audio_data = b"test_audio_data"
        await orchestrator_v2.send_audio_chunked(audio_data)
        
        orchestrator_v2.audio_manager.send_audio_chunked.assert_called_once_with(audio_data)
    
    @pytest.mark.asyncio
    async def test_handle_interruption_calls_audio_manager(self, orchestrator_v2):
        """Test that interruption delegates to AudioManager."""
        orchestrator_v2.audio_manager.interrupt_speaking = AsyncMock()
        orchestrator_v2._clear_pipeline_output = AsyncMock()
        
        await orchestrator_v2.handle_interruption("user spoke")
        
        orchestrator_v2.audio_manager.interrupt_speaking.assert_called_once()
        orchestrator_v2._clear_pipeline_output.assert_called_once()


class TestLifecycle:
    """Test lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_stop_cleans_up_resources(self, orchestrator_v2):
        """Test that stop() cleans up all resources."""
        # Setup mocks
        orchestrator_v2.pipeline = Mock()
        orchestrator_v2.pipeline.stop = AsyncMock()
        
        orchestrator_v2.audio_manager.stop = AsyncMock()
        
        orchestrator_v2.monitor_task = asyncio.create_task(asyncio.sleep(100))
        
        # Stop
        await orchestrator_v2.stop()
        
        # Verify cleanup
        orchestrator_v2.pipeline.stop.assert_called_once()
        orchestrator_v2.audio_manager.stop.assert_called_once()
        assert orchestrator_v2.monitor_task.cancelled()


class TestInputProcessing:
    """Test input audio processing."""
    
    @pytest.mark.asyncio
    async def test_process_audio_pushes_to_pipeline(self, orchestrator_v2):
        """Test that audio is pushed to pipeline."""
        import base64
        
        # Setup mock pipeline
        orchestrator_v2.pipeline = Mock()
        orchestrator_v2.pipeline.queue_frame = AsyncMock()
        
        # Test
        audio_bytes = b"test_audio"
        payload = base64.b64encode(audio_bytes).decode()
        
        await orchestrator_v2.process_audio(payload)
        
        # Verify frame was queued
        orchestrator_v2.pipeline.queue_frame.assert_called_once()
        frame = orchestrator_v2.pipeline.queue_frame.call_args[0][0]
        assert frame.data == audio_bytes


class TestManagerIntegration:
    """Test integration between V2 and Managers."""
    
    def test_audio_manager_access(self, orchestrator_v2):
        """Test that audio manager is accessible and properly configured."""
        assert orchestrator_v2.audio_manager is not None
        assert orchestrator_v2.audio_manager.client_type == "browser"
        assert orchestrator_v2.audio_manager.transport is orchestrator_v2.transport
    
    @pytest.mark.asyncio
    async def test_speaking_state_via_manager(self, orchestrator_v2):
        """Test that speaking state is managed by AudioManager."""
        # Initially not speaking
        assert not orchestrator_v2.audio_manager.is_bot_speaking
        
        # Simulate speaking
        orchestrator_v2.audio_manager.is_bot_speaking = True
        assert orchestrator_v2.audio_manager.is_bot_speaking


@pytest.mark.integration
class TestEndToEndFlow:
    """End-to-end integration tests (require mocked dependencies)."""
    
    @pytest.mark.asyncio
    async def test_audio_flow_to_websocket(self, orchestrator_v2, mock_transport):
        """Test that audio flows from send_audio_chunked to WebSocket."""
        # Start audio manager
        await orchestrator_v2.audio_manager.start()
        
        # Send audio
        audio_data = b"x" * 320  # 20ms @ 16kHz = 320 bytes
        await orchestrator_v2.send_audio_chunked(audio_data)
        
        # Wait for transmission
        await asyncio.sleep(0.1)
        
        # Verify transport.send_audio was called
        assert mock_transport.send_audio.called
        
        # Cleanup
        await orchestrator_v2.audio_manager.stop()
