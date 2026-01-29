"""
Dependency Injection Container (Clean Architecture Pro).

Manages all dependencies with lifecycle control, testing support,
and configuration-based provider selection.
"""
from dependency_injector import containers, providers as di_providers
from app.providers.azure import AzureProvider
from app.providers.groq import GroqProvider
from app.providers.azure_openai import AzureOpenAIProvider


class ServiceContainer(containers.DeclarativeContainer):
    """Main DI Container for the application."""
    
    # Configuration
    config = di_providers.Configuration()
    
    # ========== Providers (Singletons for efficiency) ==========
    azure_provider = di_providers.Singleton(AzureProvider)
    groq_provider = di_providers.Singleton(GroqProvider)
    azure_openai_provider = di_providers.Singleton(AzureOpenAIProvider)
    
    # ========== Cache Service ==========
    @staticmethod
    def _get_cache_service():
        """Lazy import cache service."""
        from app.services.cache import cache
        return cache
    
    cache_service = di_providers.Singleton(_get_cache_service)


# Global container instance
container = ServiceContainer()


# ========== Helper Functions (Public API) ==========

def get_stt_provider():
    """
    Get STT provider instance.
    
    Returns:
        STTProvider: Azure STT provider (singleton)
    """
    return container.azure_provider()


def get_llm_provider(provider_name: str = "groq"):
    """
    Get LLM provider instance based on name.
    
    Args:
        provider_name: "groq", "azure", or "azure openai"
    
    Returns:
        LLMProvider: Requested LLM provider (singleton)
    """
    provider_map = {
        "groq": container.groq_provider,
        "azure": container.azure_openai_provider,
        "azure openai": container.azure_openai_provider,
    }
    
    provider_factory = provider_map.get(provider_name.lower())
    if not provider_factory:
        # Default to Groq if unknown
        provider_factory = container.groq_provider
    
    return provider_factory()


def get_tts_provider(audio_mode: str = "twilio"):
    """
    Get TTS provider instance.
    
    Args:
        audio_mode: "browser", "twilio", or "telnyx"
    
    Returns:
        TTSProvider: Azure TTS provider (singleton)
    
    Note:
        audio_mode is passed to the provider for configuration,
        but doesn't change which provider is used (always Azure for now)
    """
    # For now always return Azure
    # In future, could have different providers based on audio_mode
    return container.azure_provider()


def get_cache_service():
    """
    Get cache service instance.
    
    Returns:
        CacheService: Redis cache service (singleton)
    """
    return container.cache_service()


# ========== Testing Support ==========

def override_llm_provider(mock_provider):
    """
    Override LLM provider for testing.
    
    Args:
        mock_provider: Mock LLM provider instance
    """
    container.groq_provider.override(mock_provider)


def override_tts_provider(mock_provider):
    """
    Override TTS provider for testing.
    
    Args:
        mock_provider: Mock TTS provider instance
    """
    container.azure_provider.override(mock_provider)


def override_stt_provider(mock_provider):
    """
    Override STT provider for testing.
    
    Args:
        mock_provider: Mock STT provider instance
    """
    container.azure_provider.override(mock_provider)


def reset_overrides():
    """Reset all testing overrides."""
    container.reset_override()
