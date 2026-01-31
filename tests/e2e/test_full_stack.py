"""
End-to-End Integration Tests - Clean Architecture Validation

Tests the full stack integration:
- VoiceOrchestratorV2 → AudioManager → WebSocket
- Config API → Database → Validation
- Pipeline flow: Audio → STT → LLM → TTS → Output
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.core.orchestrator_v2 import VoiceOrchestratorV2
from app.domain.ports.audio_transport import AudioTransport
from app.domain.ports import STTPort, LLMPort, TTSPort, ConfigRepositoryPort, CallRepositoryPort


@pytest.fixture
async def db_session():
    """Create test database session."""
    from app.db.database import AsyncSessionLocal, engine
    from app.db.models import Base
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Provide session
    async with AsyncSessionLocal() as session:
        yield session
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def mock_transport():
    """Mock WebSocket transport."""
    transport = Mock(spec=AudioTransport)
    transport.send_audio = AsyncMock()
    transport.send_json = AsyncMock()
    return transport


@pytest.mark.e2e
class TestFullPipelineFlow:
    """Test complete audio processing pipeline."""
    
    @pytest.mark.asyncio
    async def test_audio_input_to_output_flow(self, mock_transport, db_session):
        """
        E2E Test: Audio input → Pipeline → Audio output
        
        Flow:
        1. User audio arrives via WebSocket
        2. STT transcribes
        3. LLM generates response
        4. TTS synthesizes
        5. Audio sent back via WebSocket
        """
        # Create Mock Ports
        mock_stt = Mock(spec=STTPort)
        mock_stt.transcribe = AsyncMock(return_value="Hello assistant")
        
        mock_llm = Mock(spec=LLMPort)
        mock_llm.generate = AsyncMock(return_value="Hi! How can I help?")
        
        mock_tts = Mock(spec=TTSPort)
        mock_tts.synthesize = AsyncMock(return_value=b"audio_data")
        
        mock_config_repo = Mock(spec=ConfigRepositoryPort)
        mock_config_repo.get_agent_config = AsyncMock(return_value=Mock(greeting_enabled=False))
        
        mock_call_repo = Mock(spec=CallRepositoryPort)
        mock_call_repo.create_call = AsyncMock(return_value=1)
        mock_call_repo.end_call = AsyncMock()

        # Setup Orchestrator via DI
        orchestrator = VoiceOrchestratorV2(
            transport=mock_transport,
            stt_port=mock_stt,
            llm_port=mock_llm,
            tts_port=mock_tts,
            config_repo=mock_config_repo,
            call_repo=mock_call_repo,
            client_type="browser",
            initial_context="e30=" # "{}" in base64
        )
        
        await orchestrator.start()
        
        # Simulate user audio input
        import base64
        user_audio = b"x" * 1600  # 100ms @ 16kHz
        payload = base64.b64encode(user_audio).decode()
        
        await orchestrator.process_audio(payload)
        
        # Wait for processing
        await asyncio.sleep(0.5)
        
        # Verify output was sent
        assert mock_transport.send_audio.called
        
        # Cleanup
        await orchestrator.stop()
    
    @pytest.mark.asyncio
    async def test_interruption_flow(self, mock_transport):
        """
        E2E Test: User interrupts bot speech
        
        Flow:
        1. Bot is speaking
        2. User interrupts (barge-in)
        3. Audio queue cleared
        4. New response generated
        """
        # Minimal DI setup for interruption test
        mock_stt = Mock(spec=STTPort)
        mock_llm = Mock(spec=LLMPort)
        mock_tts = Mock(spec=TTSPort)
        mock_config_repo = Mock(spec=ConfigRepositoryPort)
        mock_config_repo.get_agent_config = AsyncMock(return_value=Mock())
        mock_call_repo = Mock(spec=CallRepositoryPort)
        mock_call_repo.create_call = AsyncMock(return_value=1)
        
        orchestrator = VoiceOrchestratorV2(
            transport=mock_transport,
            stt_port=mock_stt,
            llm_port=mock_llm,
            tts_port=mock_tts,
            config_repo=mock_config_repo,
            call_repo=mock_call_repo,
            client_type="browser",
            initial_context="e30="
        )
        
        # Start audio manager
        await orchestrator.audio_manager.start()
        
        # Configure FSM to allow interrupt
        orchestrator.fsm.state = "SPEAKING" # Hack just for unit expectation if FSM is strict
        # Actually in partial E2E we might rely on real FSM. 
        # But we need to ensure FSM allows transition. 
        # By default start() puts it in listening. We need to simulate speaking.
        
        # Simulate bot speaking
        orchestrator.audio_manager.is_bot_speaking = True
        orchestrator.fsm.state = "SPEAKING" # Type: ignore (String vs Enum) - assumes Enum works with str or we need Enum
        from app.domain.state import ConversationState
        orchestrator.fsm.state = ConversationState.SPEAKING
        
        await orchestrator.audio_manager.send_audio_chunked(b"x" * 320)
        
        # User interrupts
        await orchestrator.handle_interruption("user spoke")
        
        # Verify speaking stopped
        assert not orchestrator.audio_manager.is_bot_speaking
        
        # Cleanup
        await orchestrator.audio_manager.stop()


@pytest.mark.e2e
class TestConfigurationAPI:
    """Test configuration API endpoints end-to-end."""
    
    @pytest.mark.asyncio
    async def test_config_update_persistence(self, db_session):
        """
        E2E Test: Config update → Database → Retrieval
        
        Flow:
        1. Update config via API
        2. Persist to database
        3. Retrieve and verify changes
        """
        from app.services.db_service import db_service
        from app.utils.config_utils import update_profile_config
        
        # Initial config
        _config = await db_service.get_agent_config(db_session)
        
        # Update via utility
        updates = {"temperature": 0.9, "max_tokens": 2000}
        updated = await update_profile_config(db_session, "core", updates)
        
        # Verify update
        assert updated is not None
        assert updated.temperature == 0.9
        assert updated.max_tokens == 2000
        
        # Retrieve fresh from DB
        fresh = await db_service.get_agent_config(db_session)
        assert fresh.temperature == 0.9


@pytest.mark.e2e
class TestManagerIntegration:
    """Test managers in real scenarios."""
    
    @pytest.mark.asyncio
    async def test_audio_manager_background_mixing(self, mock_transport):
        """
        E2E Test: AudioManager with background audio
        
        Flow:
        1. Load background audio
        2. Send TTS audio
        3. Verify mixing occurs
        4. Audio transmitted with background
        """
        from app.core.managers import AudioManager
        
        manager = AudioManager(mock_transport, "browser")
        
        # Set background audio (mock)
        bg_audio = b"y" * 320
        manager.bg_loop_buffer = bg_audio
        
        # Start
        await manager.start()
        
        # Send audio
        tts_audio = b"x" * 320
        await manager.send_audio_chunked(tts_audio)
        
        # Wait for transmission
        await asyncio.sleep(0.2)
        
        # Verify audio sent
        assert mock_transport.send_audio.called
        
        # Cleanup
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_crm_manager_context_fetch(self):
        """
        E2E Test: CRMManager fetches contact context
        
        Flow:
        1. Create CRM manager with config
        2. Fetch context for phone number
        3. Verify context enriched
        """
        from app.core.managers import CRMManager
        
        # Mock config
        config = Mock()
        config.enable_crm = True
        config.baserow_token = "test_token"
        config.baserow_table_id = "12345"
        
        context_data = {"from": "+525551234567"}
        
        manager = CRMManager(config, context_data)
        
        # Mock HTTP request
        with patch('app.db.baserow.BaserowClient.find_contact') as mock_find:
            mock_find.return_value = {"name": "Test User", "company": "Test Co"}
            
            # Fetch context
            await manager.fetch_context("+525551234567")
            
            # Verify enrichment
            assert manager.crm_context is not None
            assert manager.crm_context.get("name") == "Test User"


@pytest.mark.e2e
class TestValueObjectsPipeline:
    """Test Value Objects in real pipeline usage."""
    
    def test_voice_config_to_tts_params(self):
        """
        E2E Test: VoiceConfig → SSML params → TTS
        
        Flow:
        1. Create VoiceConfig from DB
        2. Convert to SSML params
        3. Verify format matches TTS expectations
        """
        from app.domain.value_objects import VoiceConfig
        
        config = VoiceConfig(
            voice="es-MX-DaliaNeural",
            language="es-MX",
            style="cheerful",
            style_degree=1.5,
            rate=1.2,
            pitch=5,
            volume=75
        )
        
        # Convert to SSML params
        params = config.to_ssml_params()
        
        # Verify format
        assert params["voice"] == "es-MX-DaliaNeural"
        assert params["lang"] == "es-MX"
        assert params["style"] == "cheerful"
        assert params["style_degree"] == 1.5
        assert isinstance(params["rate"], float)
        assert isinstance(params["pitch"], int)
        assert isinstance(params["volume"], int)


@pytest.mark.e2e
@pytest.mark.slow
class TestUseCaseChaining:
    """Test Use Cases in chain."""
    
    @pytest.mark.asyncio
    async def test_generate_then_synthesize(self):
        """
        E2E Test: GenerateResponse → SynthesizeText
        
        Flow:
        1. Generate LLM response
        2. Synthesize to audio
        3. Verify audio output
        """
        from app.use_cases.voice import GenerateResponseUseCase, SynthesizeTextUseCase
        from app.domain.value_objects import VoiceConfig
        
        # Mock providers
        mock_llm = Mock()
        mock_llm.generate = AsyncMock(return_value="Generated response")
        
        mock_tts = Mock()
        mock_tts.synthesize = AsyncMock(return_value=b"audio_output")
        
        # Use cases
        generate_uc = GenerateResponseUseCase(mock_llm)
        synthesize_uc = SynthesizeTextUseCase(mock_tts)
        
        # Execute chain
        text = await generate_uc.execute("user input", [], {})
        assert text == "Generated response"
        
        voice_config = VoiceConfig.default("es-MX")
        audio = await synthesize_uc.execute(text, voice_config)
        assert audio == b"audio_output"


# Performance benchmarks
@pytest.mark.benchmark
class TestPerformance:
    """Performance tests for critical paths."""
    
    @pytest.mark.asyncio
    async def test_audio_chunk_throughput(self, mock_transport):
        """Benchmark: Audio chunking throughput."""
        from app.core.managers import AudioManager
        import time
        
        manager = AudioManager(mock_transport, "browser")
        await manager.start()
        
        # Send 10 seconds of audio (16kHz, 16-bit)
        audio_data = b"x" * 320000  # 10 sec
        
        start = time.time()
        await manager.send_audio_chunked(audio_data)
        duration = time.time() - start
        
        # Should chunk and queue in < 100ms
        assert duration < 0.1
        
        await manager.stop()
