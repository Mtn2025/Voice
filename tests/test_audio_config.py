import pytest
from app.core.audio_config import AudioConfig
from app.adapters.outbound.stt.azure_stt_adapter import AzureSTTAdapter
from app.adapters.outbound.tts.azure_tts_adapter import AzureTTSAdapter
from unittest.mock import MagicMock, patch

class TestAudioConfig:
    def test_browser_config(self):
        config = AudioConfig.for_browser()
        assert config.sample_rate == 16000
        assert config.encoding == "pcm"
    
    def test_telnyx_config(self):
        config = AudioConfig.for_telnyx()
        assert config.sample_rate == 8000
        assert config.encoding == "mulaw"

    def test_legacy_conversion(self):
        c1 = AudioConfig.from_legacy_mode("browser")
        assert c1.sample_rate == 16000
        
        c2 = AudioConfig.from_legacy_mode("unknown")
        assert c2.sample_rate == 8000  # Default to telephony

class TestAzureAdaptersRefactor:
    @patch("azure.cognitiveservices.speech.SpeechConfig")
    def test_stt_adapter_initialization(self, mock_speech_config):
        # 1. New way (AudioConfig)
        audio_config = AudioConfig.for_browser()
        adapter = AzureSTTAdapter(config=MagicMock(), audio_config=audio_config)
        assert adapter.audio_config.sample_rate == 16000

        # 2. Legacy way (audio_mode in config)
        mock_config = MagicMock()
        mock_config.audio_mode = "telnyx"
        adapter_legacy = AzureSTTAdapter(config=mock_config)
        assert adapter_legacy.audio_config.sample_rate == 8000

    @patch("azure.cognitiveservices.speech.SpeechConfig")
    def test_tts_adapter_initialization(self, mock_speech_config):
        # 1. New way (AudioConfig)
        audio_config = AudioConfig.for_browser()
        adapter = AzureTTSAdapter(config=MagicMock(), audio_config=audio_config)
        assert adapter.audio_config.sample_rate == 16000

        # 2. Legacy way (param)
        adapter_legacy = AzureTTSAdapter(config=MagicMock(), audio_mode="telnyx")
        assert adapter_legacy.audio_config.sample_rate == 8000
