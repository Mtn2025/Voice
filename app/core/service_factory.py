"""
Service Factory (Legacy Wrapper over DI Container).

This factory is maintained for backward compatibility with existing code.
New code should use the DI container directly via:
    from app.core.di_container import get_stt_provider, get_llm_provider, get_tts_provider

The factory delegates to the DI container internally, providing:
- Singleton management (via container)
- Testing support (via container overrides)
- Configuration-based provider selection
"""
from app.db.models import AgentConfig
from app.core.di_container import container


class ServiceFactory:
    """
    Factory for creating service providers (legacy interface).
    
    This class wraps the DI container to maintain backward compatibility
    with code that still uses ServiceFactory.get_*_provider() pattern.
    """
    
    @staticmethod
    def get_stt_provider(config: AgentConfig):
        """
        Get STT provider instance.
        
        Args:
            config: Agent configuration (currently unused, always returns Azure)
        
        Returns:
            STTProvider: Azure STT provider singleton
        """
        # Delegate to DI container
        return container.azure_provider()
    
    @staticmethod
    def get_tts_provider(config: AgentConfig):
        """
        Get TTS provider instance.
        
        Args:
            config: Agent configuration (client_type extracted for audio mode)
        
        Returns:
            TTSProvider: Azure TTS provider singleton
        """
        # Extract audio mode from config
        # audio_mode = getattr(config, 'client_type', 'twilio')
        
        # For now, delegate to DI container
        # (audio_mode will be passed later to create_synthesizer method)
        return container.azure_provider()
    
    @staticmethod
    def get_llm_provider(config: AgentConfig):
        """
        Get LLM provider instance based on configuration.
        
        Args:
            config: Agent configuration with llm_provider field
        
        Returns:
            LLMProvider: Groq or Azure OpenAI provider singleton
        """
        provider_name = (config.llm_provider or "groq").lower()
        
        # Map provider names to container singletons
        provider_map = {
            "groq": container.groq_provider,
            "azure": container.azure_openai_provider,
            "azure openai": container.azure_openai_provider,
        }
        
        provider_factory = provider_map.get(provider_name)
        
        if provider_factory:
            return provider_factory()
        
        # Fallback to Groq with warning
        import logging
        logging.warning(f"⚠️ Unknown LLM Provider '{provider_name}'. Defaulting to Groq.")
        return container.groq_provider()
