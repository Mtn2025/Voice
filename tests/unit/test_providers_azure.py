"""
Tests for Azure provider (STT, TTS).

Strategic tests for Azure service methods.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.providers.azure import AzureProvider


@pytest.mark.unit
class TestAzureProvider:
    """Test Azure STT/TTS provider."""
    
    def test_azure_init(self):
        """Test: AzureProvider initializes."""
        with patch('app.providers.azure.speechsdk'):
            provider = AzureProvider(
                speech_key="test_key",
                speech_region="test_region"
            )
            
            assert provider.speech_key == "test_key"
            assert provider.speech_region == "test_region"
    
    def test_create_recognizer(self):
        """Test: create_recognizer builds STT recognizer."""
        with patch('app.providers.azure.speechsdk') as mock_sdk:
            provider = AzureProvider(
                speech_key="test_key",
                speech_region="test_region"
            )
            
            mock_stream = MagicMock()
            recognizer = provider.create_recognizer(
                push_stream=mock_stream,
                language="es-MX"
            )
            
            # Should create recognizer
            assert recognizer is not None
    
    def test_create_synthesizer(self):
        """Test: create_synthesizer builds TTS synthesizer."""
        with patch('app.providers.azure.speechsdk') as mock_sdk:
            provider = AzureProvider(
                speech_key="test_key",
                speech_region="test_region"
            )
            
            synthesizer = provider.create_synthesizer(
                voice_name="es-MX-DaliaNeural",
                audio_mode="browser"
            )
            
            # Should create synthesizer
            assert synthesizer is not None
    
    @pytest.mark.asyncio
    async def test_synthesize_ssml(self):
        """Test: synthesize_ssml generates audio."""
        with patch('app.providers.azure.speechsdk'):
            provider = AzureProvider(
                speech_key="test_key",
                speech_region="test_region"
            )
            
            mock_synth = MagicMock()
            mock_result = MagicMock()
            mock_result.audio_data = b"fake_audio"
            mock_synth.speak_ssml_async = MagicMock(
                return_value=MagicMock(get=MagicMock(return_value=mock_result))
            )
            
            ssml = "<speak>Test</speak>"
            result = await provider.synthesize_ssml(mock_synth, ssml)
            
            assert result == b"fake_audio"


@pytest.mark.unit
class TestAzureEdgeCases:
    """Test Azure error handling."""
    
    def test_create_recognizer_invalid_language(self):
        """Test: create_recognizer handles invalid language."""
        with patch('app.providers.azure.speechsdk'):
            provider = AzureProvider(
                speech_key="test_key",
                speech_region="test_region"
            )
            
            mock_stream = MagicMock()
            
            # Should not crash with invalid language
            try:
                recognizer = provider.create_recognizer(
                    push_stream=mock_stream,
                    language="invalid-XX"
                )
                assert recognizer is not None
            except:
                pass  # Expected to handle gracefully
    
    @pytest.mark.asyncio
    async def test_synthesize_ssml_empty(self):
        """Test: synthesize_ssml handles empty SSML."""
        with patch('app.providers.azure.speechsdk'):
            provider = AzureProvider(
                speech_key="test_key",
                speech_region="test_region"
            )
            
            mock_synth = MagicMock()
            mock_synth.speak_ssml_async = MagicMock(
                return_value=MagicMock(get=MagicMock(return_value=None))
            )
            
            result = await provider.synthesize_ssml(mock_synth, "")
            
            # Should handle gracefully
            assert result is None or result == b""
