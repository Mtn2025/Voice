"""
Tests for Phase 2.1: Exception Translation (Infrastructure -> Domain).

Validates that adapters wrap errors in domain exceptions with metadata.
"""
import pytest
from unittest.mock import Mock, AsyncMock

from app.adapters.outbound.llm.groq_llm_adapter import GroqLLMAdapter
from app.adapters.outbound.tts.azure_tts_adapter import AzureTTSAdapter
from app.adapters.outbound.stt.azure_stt_adapter import AzureSTTAdapter
from app.domain.ports import LLMRequest, LLMException, TTSException, STTException, TTSRequest, STTConfig


class TestGroqLLMExceptionTranslation:
    """Test GroqLLMAdapter exception wrapping."""
    
    @pytest.mark.asyncio
    async def test_generic_error_wrapped_in_llm_exception(self):
        """Verify generic errors are wrapped in LLMException with metadata."""
        adapter = GroqLLMAdapter()
        adapter.groq_provider.get_stream = AsyncMock(side_effect=Exception("Test error"))
        
        request = LLMRequest(messages=[], model="llama-3.3-70b-versatile")
        
        with pytest.raises(LLMException) as exc_info:
            async for _ in adapter.generate_stream(request):
                pass
        
        exc = exc_info.value
        assert exc.provider == "groq"
        assert exc.original_error is not None


class TestAzureTTSExceptionTranslation:
    """Test AzureTTSAdapter exception wrapping."""
    
    @pytest.mark.asyncio
    async def test_empty_audio_raises_tts_exception(self):
        """Verify empty audio returns raise TTSException retryable=True."""
        adapter = AzureTTSAdapter(audio_mode="browser")
        adapter.azure_provider.synthesize_ssml = AsyncMock(return_value=None)
        adapter._synthesizer = Mock()
        
        request = TTSRequest(text="Test", voice_id="es-MX-DaliaNeural", language="es-MX")
        
        with pytest.raises(TTSException) as exc_info:
            await adapter.synthesize(request)
        
        assert exc_info.value.retryable is True
        assert exc_info.value.provider == "azure"


class TestAzureSTTExceptionTranslation:
    """Test AzureSTTAdapter exception wrapping."""
    
    def test_recognizer_creation_error_wrapped(self):
        """Verify errors creating recognizer are wrapped."""
        adapter = AzureSTTAdapter()
        adapter.azure_provider.create_recognizer = Mock(side_effect=Exception("Connection failed"))
        
        config = STTConfig(language="es-MX", audio_mode="browser")
        
        with pytest.raises(STTException) as exc_info:
            adapter.create_recognizer(config)
        
        assert exc_info.value.provider == "azure"


class TestExceptionMetadata:
    """Test domain exception metadata."""
    
    def test_llm_exception_str_repr(self):
        """Verify LLMException __str__ includes provider and retryability."""
        exc = LLMException("Test error", retryable=True, provider="groq")
        str_repr = str(exc)
        assert "[groq]" in str_repr
        assert "retryable" in str_repr.lower()
    
    def test_exception_attributes(self):
        """Verify all domain exceptions have required attributes."""
        exceptions = [
            LLMException("Test", retryable=True, provider="groq", original_error=ValueError()),
            TTSException("Test", retryable=False, provider="azure"),
            STTException("Test", retryable=True, provider="deepgram")
        ]
        
        for exc in exceptions:
            assert hasattr(exc, "retryable")
            assert hasattr(exc, "provider")
            assert hasattr(exc, "original_error")
            assert exc.provider in ["groq", "azure", "deepgram"]
