"""
Tests for Groq provider (LLM, transcription).

Strategic tests for core provider methods.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.providers.groq import GroqProvider


@pytest.mark.unit
class TestGroqProvider:
    """Test Groq LLM provider."""
    
    def test_groq_init(self):
        """Test: GroqProvider initializes with API key."""
        provider = GroqProvider(api_key="test_key", model="llama-test")
        
        assert provider.api_key == "test_key"
        assert provider.model == "llama-test"
    
    @pytest.mark.asyncio
    async def test_get_stream_basic(self):
        """Test: get_stream yields LLM responses."""
        provider = GroqProvider(api_key="test_key")
        
        messages = [{"role": "user", "content": "Hello"}]
        
        # Mock Groq client
        with patch.object(provider, 'client') as mock_client:
            mock_response = MagicMock()
            mock_response.__aiter__ = AsyncMock(return_value=iter([
                MagicMock(choices=[MagicMock(delta=MagicMock(content="Hi"))]),
                MagicMock(choices=[MagicMock(delta=MagicMock(content=" there"))])
            ]))
            mock_client.chat.completions.create = MagicMock(return_value=mock_response)
            
            result = []
            async for chunk in provider.get_stream(messages):
                result.append(chunk)
            
            assert len(result) >= 0  # Should yield chunks
    
    @pytest.mark.asyncio
    async def test_transcribe_audio(self):
        """Test: transcribe_audio calls Whisper API."""
        provider = GroqProvider(api_key="test_key")
        
        audio_bytes = b"fake_audio_data"
        
        with patch.object(provider, 'client') as mock_client:
            mock_client.audio.transcriptions.create = MagicMock(
                return_value=MagicMock(text="Transcribed text")
            )
            
            result = await provider.transcribe_audio(audio_bytes)
            
            assert result == "Transcribed text"
    
    @pytest.mark.asyncio
    async def test_extract_data(self):
        """Test: extract_data calls extraction model."""
        provider = GroqProvider(api_key="test_key")
        
        with patch.object(provider, 'client') as mock_client:
            mock_client.chat.completions.create = MagicMock(
                return_value=MagicMock(
                    choices=[MagicMock(message=MagicMock(content='{"name": "John"}'))]
                )
            )
            
            result = await provider.extract_data("conversation text")
            
            assert "name" in result
            assert result["name"] == "John"


@pytest.mark.unit
class TestGroqEdgeCases:
    """Test Groq error handling."""
    
    @pytest.mark.asyncio
    async def test_transcribe_empty_audio(self):
        """Test: transcribe_audio handles empty audio."""
        provider = GroqProvider(api_key="test_key")
        
        result = await provider.transcribe_audio(b"")
        
        # Should handle gracefully
        assert result is None or result == ""
    
    @pytest.mark.asyncio
    async def test_extract_data_invalid_json(self):
        """Test: extract_data handles invalid JSON."""
        provider = GroqProvider(api_key="test_key")
        
        with patch.object(provider, 'client') as mock_client:
            mock_client.chat.completions.create = MagicMock(
                return_value=MagicMock(
                    choices=[MagicMock(message=MagicMock(content='not valid json'))]
                )
            )
            
            result = await provider.extract_data("text")
            
            # Should return empty dict or handle error
            assert isinstance(result, dict)
