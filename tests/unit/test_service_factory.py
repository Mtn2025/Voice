"""
Tests unitarios para ServiceFactory.

NOTA: Estos tests pueden fallar si audioop no está disponible (Python 3.13+)
ya que ServiceFactory importa providers que usan orchestrator.py
"""

# Verificar si audioop está disponible
import importlib.util

import pytest

AUDIOOP_AVAILABLE = importlib.util.find_spec("audioop") is not None

if AUDIOOP_AVAILABLE:
    try:
        from app.core.service_factory import ServiceFactory
        FACTORY_AVAILABLE = True
    except (ImportError, ModuleNotFoundError):
        FACTORY_AVAILABLE = False
else:
    FACTORY_AVAILABLE = False


@pytest.mark.unit
@pytest.mark.skipif(not FACTORY_AVAILABLE, reason="ServiceFactory requires audioop (Python 3.13+)")
class TestServiceFactory:
    """Suite de tests para la fábrica de servicios."""

    def test_factory_initialization(self):
        """Test: ServiceFactory se puede instanciar."""
        factory = ServiceFactory()
        assert factory is not None

    def test_get_stt_provider_azure(self):
        """Test: Obtener provider STT Azure."""
        factory = ServiceFactory()
        provider = factory.get_stt_provider("azure")

        assert provider is not None
        assert hasattr(provider, 'recognize_once_async')

    def test_get_tts_provider_azure(self):
        """Test: Obtener provider TTS Azure."""
        factory = ServiceFactory()
        provider = factory.get_tts_provider("azure")

        assert provider is not None
        assert hasattr(provider, 'synthesize_to_stream')

    def test_get_llm_provider_groq(self):
        """Test: Obtener provider LLM Groq."""
        factory = ServiceFactory()
        provider = factory.get_llm_provider("groq")

        assert provider is not None
        assert hasattr(provider, 'chat_completion_stream')
