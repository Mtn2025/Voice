"""Unit tests for DI Container."""
import pytest
from unittest.mock import Mock
from app.core.di_container import (
    container,
    get_stt_provider,
    get_llm_provider,
    get_tts_provider,
    override_llm_provider,
    reset_overrides
)


def test_container_exists():
    """Test that container instance exists."""
    assert container is not None


def test_get_stt_provider_returns_azure():
    """Test STT provider is Azure singleton."""
    provider1 = get_stt_provider()
    provider2 = get_stt_provider()
    
    # Should be same instance (singleton)
    assert provider1 is provider2
    assert hasattr(provider1, 'create_recognizer')


def test_get_llm_provider_groq():
    """Test LLM provider returns Groq by default."""
    provider = get_llm_provider("groq")
    
    assert provider is not None
    assert hasattr(provider, 'get_stream')


def test_get_llm_provider_azure():
    """Test LLM provider can return Azure OpenAI."""
    provider = get_llm_provider("azure")
    
    assert provider is not None
    assert hasattr(provider, 'get_stream')


def test_get_llm_provider_unknown_defaults_to_groq():
    """Test unknown LLM provider defaults to Groq."""
    provider = get_llm_provider("unknown_provider")
    
    # Should default to Groq
    groq_provider = get_llm_provider("groq")
    assert provider is groq_provider


def test_get_tts_provider_returns_azure():
    """Test TTS provider is Azure singleton."""
    provider1 = get_tts_provider("twilio")
    provider2 = get_tts_provider("browser")
    
    # Should be same instance (singleton) regardless of audio_mode
    assert provider1 is provider2
    assert hasattr(provider1, 'create_synthesizer')


def test_override_llm_provider():
    """Test overriding LLM provider for testing."""
    # Create mock
    mock_llm = Mock()
    mock_llm.get_stream = Mock()
    
    # Override
    override_llm_provider(mock_llm)
    
    # Get provider (should be mocked)
    provider = get_llm_provider("groq")
    assert provider is mock_llm
    
    # Reset
    reset_overrides()
    
    # Should be real provider again
    provider_after_reset = get_llm_provider("groq")
    assert provider_after_reset is not mock_llm


def test_providers_are_singletons():
    """Test that providers are singletons (same instance)."""
    stt1 = get_stt_provider()
    stt2 = get_stt_provider()
    assert stt1 is stt2
    
    tts1 = get_tts_provider()
    tts2 = get_tts_provider()
    assert tts1 is tts2
    
    llm1 = get_llm_provider("groq")
    llm2 = get_llm_provider("groq")
    assert llm1 is llm2
