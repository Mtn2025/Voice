"""
Unit Tests for Provider Registry.

Tests config-driven provider selection and extensibility.
"""
import pytest
from app.infrastructure.provider_registry import ProviderRegistry, get_provider_registry
from app.domain.ports.provider_config import (
    STTProviderConfig,
    LLMProviderConfig,
    TTSProviderConfig
)
from app.domain.ports import STTPort, LLMPort, TTSPort


class TestProviderRegistry:
    """Test suite for ProviderRegistry."""
    
    def setup_method(self):
        """Create fresh registry for each test."""
        self.registry = ProviderRegistry()
    
    # -------------------------------------------------------------------------
    # Registration Tests
    # -------------------------------------------------------------------------
    
    def test_register_stt_provider(self):
        """Test STT provider registration."""
        # Mock factory
        def mock_factory(config):
            return "MockSTTAdapter"
        
        self.registry.register_stt("mock_stt", mock_factory)
        
        providers = self.registry.get_available_providers()
        assert "mock_stt" in providers['stt']
    
    def test_register_llm_provider(self):
        """Test LLM provider registration."""
        def mock_factory(config):
            return "MockLLMAdapter"
        
        self.registry.register_llm("mock_llm", mock_factory)
        
        providers = self.registry.get_available_providers()
        assert "mock_llm" in providers['llm']
    
    def test_register_tts_provider(self):
        """Test TTS provider registration."""
        def mock_factory(config):
            return "MockTTSAdapter"
        
        self.registry.register_tts("mock_tts", mock_factory)
        
        providers = self.registry.get_available_providers()
        assert "mock_tts" in providers['tts']
    
    # -------------------------------------------------------------------------
    # Creation Tests
    # -------------------------------------------------------------------------
    
    def test_create_stt_with_valid_provider(self):
        """Test creating STT adapter with registered provider."""
        # Register mock factory
        def mock_factory(config):
            assert config.provider == "test_stt"
            assert config.api_key == "test_key"
            return "MockSTTAdapter"
        
        self.registry.register_stt("test_stt", mock_factory)
        
        config = STTProviderConfig(
            provider="test_stt",
            api_key="test_key",
            region="test_region"
        )
        
        adapter = self.registry.create_stt(config)
        assert adapter == "MockSTTAdapter"
    
    def test_create_llm_with_valid_provider(self):
        """Test creating LLM adapter with registered provider."""
        def mock_factory(config):
            assert config.provider == "test_llm"
            assert config.model == "test_model"
            return "MockLLMAdapter"
        
        self.registry.register_llm("test_llm", mock_factory)
        
        config = LLMProviderConfig(
            provider="test_llm",
            api_key="test_key",
            model="test_model"
        )
        
        adapter = self.registry.create_llm(config)
        assert adapter == "MockLLMAdapter"
    
    def test_create_tts_with_valid_provider(self):
        """Test creating TTS adapter with registered provider."""
        def mock_factory(config):
            assert config.provider == "test_tts"
            assert config.audio_mode == "twilio"
            return "MockTTSAdapter"
        
        self.registry.register_tts("test_tts", mock_factory)
        
        config = TTSProviderConfig(
            provider="test_tts",
            api_key="test_key",
            region="test_region",
            audio_mode="twilio"
        )
        
        adapter = self.registry.create_tts(config)
        assert adapter == "MockTTSAdapter"
    
    # -------------------------------------------------------------------------
    # Error Handling Tests
    # -------------------------------------------------------------------------
    
    def test_create_stt_with_unknown_provider_raises(self):
        """Test that unknown STT provider raises ValueError."""
        config = STTProviderConfig(
            provider="unknown_provider",
            api_key="test_key"
        )
        
        with pytest.raises(ValueError) as exc_info:
            self.registry.create_stt(config)
        
        assert "Unknown STT provider: 'unknown_provider'" in str(exc_info.value)
        assert "Available:" in str(exc_info.value)
    
    def test_create_llm_with_unknown_provider_raises(self):
        """Test that unknown LLM provider raises ValueError."""
        config = LLMProviderConfig(
            provider="invalid_llm",
            api_key="test_key"
        )
        
        with pytest.raises(ValueError) as exc_info:
            self.registry.create_llm(config)
        
        assert "Unknown LLM provider: 'invalid_llm'" in str(exc_info.value)
    
    def test_create_tts_with_unknown_provider_raises(self):
        """Test that unknown TTS provider raises ValueError."""
        config = TTSProviderConfig(
            provider="invalid_tts",
            api_key="test_key"
        )
        
        with pytest.raises(ValueError) as exc_info:
            self.registry.create_tts(config)
        
        assert "Unknown TTS provider: 'invalid_tts'" in str(exc_info.value)
    
    # -------------------------------------------------------------------------
    # Introspection Tests
    # -------------------------------------------------------------------------
    
    def test_get_available_providers_empty(self):
        """Test getting available providers from empty registry."""
        providers = self.registry.get_available_providers()
        
        assert providers == {
            'stt': [],
            'llm': [],
            'tts': []
        }
    
    def test_get_available_providers_with_registrations(self):
        """Test getting available providers after registration."""
        self.registry.register_stt("azure", lambda c: "Azure")
        self.registry.register_stt("google", lambda c: "Google")
        self.registry.register_llm("groq", lambda c: "Groq")
        self.registry.register_tts("elevenlabs", lambda c: "ElevenLabs")
        
        providers = self.registry.get_available_providers()
        
        assert set(providers['stt']) == {"azure", "google"}
        assert providers['llm'] == ["groq"]
        assert providers['tts'] == ["elevenlabs"]
    
    # -------------------------------------------------------------------------
    # Global Registry Tests
    # -------------------------------------------------------------------------
    
    def test_get_provider_registry_returns_singleton(self):
        """Test that get_provider_registry returns same instance."""
        registry1 = get_provider_registry()
        registry2 = get_provider_registry()
        
        assert registry1 is registry2
    
    # -------------------------------------------------------------------------
    # Config Object Tests
    # -------------------------------------------------------------------------
    
    def test_stt_config_with_provider_options(self):
        """Test STTProviderConfig with provider_options."""
        config = STTProviderConfig(
            provider="azure",
            api_key="test_key",
            region="eastus",
            provider_options={"custom_param": "value"}
        )
        
        assert config.provider_options["custom_param"] == "value"
    
    def test_llm_config_with_provider_options(self):
        """Test LLMProviderConfig with provider_options."""
        config = LLMProviderConfig(
            provider="groq",
            api_key="test_key",
            model="llama-3.3-70b",
            provider_options={"streaming": True}
        )
        
        assert config.provider_options["streaming"] is True
    
    def test_tts_config_with_provider_options(self):
        """Test TTSProviderConfig with provider_options."""
        config = TTSProviderConfig(
            provider="azure",
            api_key="test_key",
            audio_mode="twilio",
            provider_options={"ssml_enabled": True}
        )
        
        assert config.provider_options["ssml_enabled"] is True


class TestProviderConfigObjects:
    """Test suite for provider config dataclasses."""
    
    def test_stt_config_defaults(self):
        """Test STTProviderConfig default values."""
        config = STTProviderConfig(
            provider="azure",
            api_key="test_key"
        )
        
        assert config.language == "es-MX"
        assert config.sample_rate == 8000
        assert config.region is None
        assert config.provider_options == {}
    
    def test_llm_config_defaults(self):
        """Test LLMProviderConfig default values."""
        config = LLMProviderConfig(
            provider="groq",
            api_key="test_key"
        )
        
        assert config.model == "llama-3.3-70b-versatile"
        assert config.temperature == 0.7
        assert config.max_tokens == 2000
        assert config.provider_options == {}
    
    def test_tts_config_defaults(self):
        """Test TTSProviderConfig default values."""
        config = TTSProviderConfig(
            provider="azure",
            api_key="test_key"
        )
        
        assert config.audio_mode == "twilio"
        assert config.region is None
        assert config.provider_options == {}
