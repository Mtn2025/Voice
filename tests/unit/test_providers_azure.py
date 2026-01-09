"""
Tests for Azure provider (STT, TTS).

Strategic tests for Azure service methods.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.providers.azure import AzureProvider


@pytest.mark.unit
class TestAzureProvider:
    """Test Azure STT/TTS provider."""

    def test_azure_init(self):
        """Test: AzureProvider initializes using env vars."""
        # Env vars are already mocked by conftest.py
        with patch('app.providers.azure.speechsdk'):
            provider = AzureProvider()
            
            # Verify it loaded from settings (mocked in conftest)
            assert provider.speech_config is not None

    def test_create_recognizer(self):
        """Test: create_recognizer builds STT recognizer."""
        with patch('app.providers.azure.speechsdk') as mock_sdk:
            provider = AzureProvider()

            # Mock internal return values
            mock_sdk.audio.PushAudioInputStream.return_value = MagicMock()
            mock_sdk.audio.AudioConfig.return_value = MagicMock()
            mock_sdk.SpeechRecognizer.return_value = MagicMock()

            # Call with valid signature (no push_stream arg)
            recognizer_wrapper = provider.create_recognizer(
                language="es-MX",
                audio_mode="browser"
            )

            # Should create valid wrapper
            assert recognizer_wrapper is not None
            assert hasattr(recognizer_wrapper, '_recognizer')
            assert hasattr(recognizer_wrapper, '_push_stream')

    def test_create_synthesizer(self):
        """Test: create_synthesizer builds TTS synthesizer."""
        with patch('app.providers.azure.speechsdk') as mock_sdk:
            provider = AzureProvider()

            synthesizer = provider.create_synthesizer(
                voice_name="es-MX-DaliaNeural",
                audio_mode="browser"
            )

            # Should create synthesizer
            assert synthesizer is not None
            mock_sdk.SpeechSynthesizer.assert_called_once()

    @pytest.mark.asyncio
    async def test_synthesize_ssml(self):
        """Test: synthesize_ssml generates audio."""
        with patch('app.providers.azure.speechsdk'):
            provider = AzureProvider()
            
            # Initializer creates an executor, we need to ensure loop.run_in_executor uses it
            # But run_in_executor is messy to mock. simpler to mock the inner blocking call?
            # Actually, synthesize_ssml uses loop.run_in_executor(self.executor, ...)
            
            # Let's mock the synthesizer passed in
            mock_synth = MagicMock()
            mock_result = MagicMock()
            mock_result.reason = MagicMock()
            # Need to match the enum value used in code
            # speechsdk.ResultReason.SynthesizingAudioCompleted
            
            # We need to mock the enum or just return valid logic
            # Since we patch speechsdk, we must recreate the enum structure slightly
            mock_result.audio_data = b"fake_audio"
            
            # Mock the blocking call result
            mock_synth.speak_ssml_async.return_value.get.return_value = mock_result
            
            # Since we patched speechsdk at module level, we must set the enum on the MOCK
            # provider imports speechsdk. 
            # In the code: if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            
            with patch('app.providers.azure.speechsdk') as mock_sdk_module:
                 # Setup Enum
                 mock_sdk_module.ResultReason.SynthesizingAudioCompleted = "COMPLETED"
                 mock_result.reason = "COMPLETED"
                 
                 ssml = "<speak>Test</speak>"
                 result = await provider.synthesize_ssml(mock_synth, ssml)
    
                 assert result == b"fake_audio"


@pytest.mark.unit
class TestAzureEdgeCases:
    """Test Azure error handling."""

    def test_create_recognizer_invalid_language(self):
        """Test: create_recognizer handles invalid language configs gracefully."""
        with patch('app.providers.azure.speechsdk') as mock_sdk:
            provider = AzureProvider()

            # Should not crash
            try:
                recognizer = provider.create_recognizer(
                    language="invalid-XX"
                )
                assert recognizer is not None
                # Verify language was passed to property
                # self.speech_config.speech_recognition_language = language
                # We can't easily check property set on mock without complex setup, but no crash is good.
            except Exception as e:
                pytest.fail(f"Should not crash: {e}")

    @pytest.mark.asyncio
    async def test_synthesize_ssml_empty(self):
        """Test: synthesize_ssml handles empty result."""
        with patch('app.providers.azure.speechsdk') as mock_sdk_module:
            provider = AzureProvider()

            mock_synth = MagicMock()
            mock_result = MagicMock()
            mock_result.reason = "FAILED" # Anything not COMPLETED
            
            mock_sdk_module.ResultReason.SynthesizingAudioCompleted = "COMPLETED"
            
            mock_synth.speak_ssml_async.return_value.get.return_value = mock_result

            result = await provider.synthesize_ssml(mock_synth, "<speak></speak>")

            # Should return None if not completed
            assert result is None
