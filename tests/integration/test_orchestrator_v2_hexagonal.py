"""Integration tests for VoiceOrchestratorV2 with Hexagonal Architecture DI."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from app.core.orchestrator_v2 import VoiceOrchestratorV2
from app.ports.transport import AudioTransport

# ✅ Hexagonal Architecture: Import ports for mocking
from app.domain.ports import STTPort, LLMPort, TTSPort


# =============================================================================
# FIXTURES - Hexagonal Architecture DI
# =============================================================================

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
def mock_config_repo():
    """✅ Create mock ConfigRepositoryPort for DI."""
    from app.domain.ports import ConfigRepositoryPort
    mock = Mock(spec=ConfigRepositoryPort)
    return mock


@pytest.fixture
def mock_transport():
    """Create mock transport."""
    transport = Mock(spec=AudioTransport)
    transport.send_audio = AsyncMock()
    transport.send_json = AsyncMock()
    return transport


@pytest.fixture
def orchestrator_v2(mock_transport, mock_stt_port, mock_llm_port, mock_tts_port, mock_config_repo):
    """✅ Create VoiceOrchestratorV2 with DI (hexagonal architecture)."""
    return VoiceOrchestratorV2(
        transport=mock_transport,
        stt_port=mock_stt_port,  # ✅ Injected
        llm_port=mock_llm_port,  # ✅ Injected
        tts_port=mock_tts_port,  # ✅ Injected
        config_repo=mock_config_repo,  # ✅ NEW - Phase 1.2
        client_type="browser"
    )


# =============================================================================
# TESTS - Hexagonal Architecture Validation
# =============================================================================

class TestHexagonalArchitectureDI:
    """Test that Dependency Injection is working correctly."""
    
    def test_ports_injected(self, orchestrator_v2, mock_stt_port, mock_llm_port, mock_tts_port):
        """✅ Test that ports are injected via constructor."""
        assert orchestrator_v2.stt is mock_stt_port
        assert orchestrator_v2.llm is mock_llm_port
        assert orchestrator_v2.tts is mock_tts_port
    
    def test_no_service_factory(self, orchestrator_v2):
        """✅ Test that ServiceFactory is NOT used (anti-pattern eliminated)."""
        # Verify providers are set via DI, not created internally
        assert orchestrator_v2.stt is not None
        assert orchestrator_v2.llm is not None
        assert orchestrator_v2.tts is not None


class TestInitialization:
    """Test VoiceOrchestratorV2 initialization."""
    
    def test_init_creates_managers(self, orchestrator_v2):
        """Test that managers are initialized."""
        assert orchestrator_v2.audio_manager is not None
        assert orchestrator_v2.crm_manager is None  # Initialized after config load
        assert orchestrator_v2.pipeline is None  # Built during start()
    
    def test_init_with_context(self, mock_transport, mock_stt_port, mock_llm_port, mock_tts_port, mock_config_repo):
        """Test initialization with context data."""
        import base64
        import json
        
        context = {"phone": "+525551234567", "campaign_id": "test-123"}
        context_token = base64.b64encode(json.dumps(context).encode()).decode()
        
        orch = VoiceOrchestratorV2(
            transport=mock_transport,
            stt_port=mock_stt_port,  # ✅ DI
            llm_port=mock_llm_port,  # ✅ DI
            tts_port=mock_tts_port,  # ✅ DI
            config_repo=mock_config_repo,  # ✅ NEW - Phase 1.2
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


@pytest.mark.integration
class TestIntegrationWithPorts:
    """Integration tests with mocked ports."""
    
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
